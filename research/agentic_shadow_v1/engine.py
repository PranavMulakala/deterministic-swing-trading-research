"""Network-free, integer-cent shadow accounting. Agents have no execution API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import hashlib
import json
import sqlite3
from contextlib import contextmanager

from swingbot.safe_paths import require_no_symlink_components

ROOT = Path(__file__).resolve().parent
ET = ZoneInfo('America/New_York')
ARMS = ('deterministic', 'analyst', 'analyst_critic')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def stamp(value):
    if not isinstance(value, str):
        raise ValueError('invalid_timestamp')
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('naive_timestamp')
    return t.astimezone(timezone.utc)


def integer(value, low=0):
    if type(value) is not int or value < low:
        raise ValueError('invalid_integer')
    return value


def config():
    freeze = json.loads((ROOT / 'FREEZE.json').read_text())
    for name, expected in freeze['files'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('frozen_rules_changed')
    return json.loads((ROOT / 'config.json').read_text())


def evidence(item, at, max_age=None):
    """Normalized content is retained and bound to its embedded source payload."""
    p = item['provenance']
    if not all(isinstance(p[k], str) and p[k] for k in ('source', 'feed')):
        raise ValueError('missing_provenance')
    published, received = stamp(p['published_at']), stamp(p['received_at'])
    if published > received or received > at:
        raise ValueError('future_information')
    if max_age is not None and (at - published).total_seconds() > max_age:
        raise ValueError('stale_evidence')
    raw = {k: v for k, v in item.items() if k != 'provenance'}
    if p['raw'] != raw or p['sha256'] != digest(raw):
        raise ValueError('payload_hash_mismatch')
    return p


def quote(item, at, cfg, *, entry=False):
    evidence(item, at, cfg['max_quote_age_seconds'])
    t = stamp(item['market_at'])
    if t > stamp(item['provenance']['published_at']) or t > at:
        raise ValueError('future_quote')
    if (at - t).total_seconds() > cfg['max_quote_age_seconds']:
        raise ValueError('stale_quote')
    bid, ask = integer(item['bid_cents']), integer(item['ask_cents'], 1)
    bs, az = integer(item['bid_size']), integer(item['ask_size'])
    if bid > ask or item['condition'] != 'regular':
        raise ValueError('invalid_quote')
    if entry and (bid == 0 or bs < 1 or az < 1 or ask - bid > cfg['max_spread_cents']
                  or (ask-bid)*10000 > cfg['max_spread_bps']*ask):
        raise ValueError('illiquid_quote')
    return bid, ask, bs, az, t


def session_close(packet, at, cfg, *, require_open=True):
    cal = packet['calendar']
    evidence(cal, at, cfg['max_reference_age_seconds'])
    opening, closing = stamp(cal['open']), stamp(cal['close'])
    day = at.astimezone(ET).date()
    if (cal['date'] != day.isoformat() or opening >= closing
            or opening.astimezone(ET).date() != day or closing.astimezone(ET).date() != day):
        raise ValueError('invalid_calendar')
    if require_open and not opening <= at < closing:
        raise ValueError('outside_verified_session')
    return closing


def validate_reference(packet, at, cfg):
    closing = session_close(packet, at, cfg)
    events = packet['events']
    evidence(events, at, cfg['max_reference_age_seconds'])
    if events['symbol'] != packet['symbol'] or events['earnings'] != 'not_applicable_etf':
        raise ValueError('earnings_event_or_unknown')
    if events['corporate_actions'] != 'clear' or stamp(events['coverage_end']) < closing:
        raise ValueError('event_coverage_unknown')
    news = packet['news']
    evidence(news, at, 3600)
    if news['complete'] is not True or news['symbol'] != packet['symbol']:
        raise ValueError('news_coverage_unknown')
    for item in news['items']:
        evidence(item, at)
        if not item['url'].startswith('https://') or not item['headline']:
            raise ValueError('missing_news_provenance')
    return closing


def contract_valid(c, symbol, at, cfg):
    evidence(c, at, cfg['max_reference_age_seconds'])
    if c['underlying'] != symbol or c['multiplier'] != 100 or type(c['multiplier']) is not int:
        raise ValueError('contract_identity')
    if c['adjusted'] is not False or c['currency'] != 'USD' or c['style'] != 'american':
        raise ValueError('unsupported_contract')
    if c['right'] not in ('C', 'P'):
        raise ValueError('unsupported_contract')
    strike = integer(c['strike_mills'], 1)
    expiry = datetime.fromisoformat(c['expiry']).date()
    if c['expiry'] != expiry.isoformat() or stamp(c['expiry_at']).astimezone(ET).date() != expiry:
        raise ValueError('invalid_expiry_reference')
    expected = f"{symbol}{expiry:%y%m%d}{c['right']}{strike:08d}"
    if c['symbol'] != expected:
        raise ValueError('contract_identity')
    return expiry


def select(packet, at, cfg):
    """Deterministic screening and sizing happen before any agent proposal."""
    try:
        if packet['symbol'] not in cfg['universe']:
            raise ValueError('outside_universe')
        closing = validate_reference(packet, at, cfg)
        local = at.astimezone(ET).strftime('%H:%M')
        if not cfg['entry_start_et'] <= local < cfg['entry_end_et']:
            raise ValueError('outside_entry_window')
        if at >= closing - timedelta(minutes=cfg['close_buffer_minutes']):
            raise ValueError('close_buffer')
        u = packet['underlying']
        evidence(u, at, cfg['max_quote_age_seconds'])
        if u['symbol'] != packet['symbol'] or stamp(u['market_at']) > stamp(u['provenance']['published_at']) or (at-stamp(u['market_at'])).total_seconds()>30:
            raise ValueError('underlying_identity_or_stale')
        price = integer(u['price_mills'], 1)
        bars = packet['bars']
        if len(bars) != 3:
            raise ValueError('missing_bars')
        for b in bars:
            evidence(b, at, 1200)
            if b['symbol'] != packet['symbol'] or stamp(b['end']) > stamp(b['provenance']['published_at']):
                raise ValueError('future_or_wrong_bar')
            integer(b['close_mills'], 1)
        ends = [stamp(b['end']) for b in bars]
        if any(ends[i+1]-ends[i] != timedelta(minutes=5) for i in range(2)) or not 0 <= (at-ends[-1]).total_seconds() <= 300:
            raise ValueError('missing_or_stale_bars')
        a,b,c = [b['close_mills'] for b in bars]
        direction = 'C' if a < b < c and (c-a)*10000 >= a*cfg['momentum_bps'] and price >= c else (
            'P' if a > b > c and (a-c)*10000 >= a*cfg['momentum_bps'] and price <= c else None)
        if direction is None:
            raise ValueError('no_momentum_signal')
        chain = packet['chain']
        evidence(chain, at, cfg['max_quote_age_seconds'])
        if chain['complete'] is not True or chain['symbol'] != packet['symbol']:
            raise ValueError('incomplete_chain')
        candidates, rejections, seen = [], [], set()
        for row in chain['contracts']:
            try:
                ct, q = row['contract'], row['quote']
                if ct['symbol'] in seen:
                    raise ValueError('duplicate_contract')
                seen.add(ct['symbol'])
                expiry = contract_valid(ct, packet['symbol'], at, cfg)
                dte = (expiry - at.astimezone(ET).date()).days
                if ct['right'] != direction or not cfg['dte_min'] <= dte <= cfg['dte_max']:
                    raise ValueError('right_or_expiry')
                strike = ct['strike_mills']
                otm = (strike-price) if direction == 'C' else (price-strike)
                if not 0 <= otm*10000 <= price*cfg['max_otm_bps']:
                    raise ValueError('moneyness')
                if integer(ct['open_interest']) < cfg['min_open_interest'] or integer(q['volume']) < cfg['min_volume']:
                    raise ValueError('illiquid_contract')
                if q['symbol'] != ct['symbol']:
                    raise ValueError('quote_identity')
                _,ask,_,_,_ = quote(q, at, cfg, entry=True)
                limit = ask + cfg['entry_slippage_cents']
                loss = limit*100 + 2*cfg['fee_per_contract_cents']
                if loss > cfg['max_contractual_loss_cents']:
                    raise ValueError('risk_budget')
                candidates.append({'contract':ct,'limit_cents':limit,'loss_cents':loss,
                                   'close_at':closing.isoformat(),'quantity':1})
            except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
                reason = str(exc) if isinstance(exc, ValueError) else 'missing_contract_data'
                rejections.append(reason)
        # Ambiguous chain identity poisons the packet, never choose first duplicate.
        if 'duplicate_contract' in rejections:
            raise ValueError('duplicate_contract')
        candidates.sort(key=lambda x:(x['contract']['expiry'],abs(x['contract']['strike_mills']-price),x['contract']['symbol']))
        return (candidates[0] if candidates else None), (None if candidates else 'no_eligible_contract'), rejections
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
        return None, str(exc) if isinstance(exc, ValueError) else 'missing_data', []


def mock_proposal(role, packet_hash):
    return {'role':role, 'action':'accept', 'confidence':50,
            'thesis':'Fixture response for proposal-path verification only.',
            'counterargument':'Momentum may reverse and option costs may exceed the move.',
            'evidence':[packet_hash], 'model':'mock-v1'}


def validate_proposal(p, role, packet_hash):
    if set(p) != {'role','action','confidence','thesis','counterargument','evidence','model'}:
        raise ValueError('invalid_proposal_schema')
    if p['role'] != role or p['action'] not in ('accept','abstain','veto') or p['model'] != 'mock-v1':
        raise ValueError('invalid_proposal_schema')
    if type(p['confidence']) is not int or not 0 <= p['confidence'] <= 100:
        raise ValueError('invalid_proposal_schema')
    if p['evidence'] != [packet_hash] or not all(isinstance(p[k],str) and 0<len(p[k])<=2000 for k in ('thesis','counterargument')):
        raise ValueError('ungrounded_proposal')
    return p['action'] == 'accept'


def initial(cfg):
    return {arm:{'cash_cents':cfg['capital_cents'], 'position':None,'pending':None,
                 'realized_cents':0,'fees_cents':0,'slippage_cents':0,'spread_cents':0,
                 'equity_cents':cfg['capital_cents'],'peak_cents':cfg['capital_cents'],
                 'max_drawdown_cents':0,'day':None,'day_start_cents':cfg['capital_cents'],
                 'daily_pause':False,'experiment_pause':False,'unknown_mark':False,
                 'fills':0,'closed_trades':0,'breaches':[]}
            for arm in ARMS}


def find_quote(packet, symbol, at, cfg):
    rows = [r for r in packet.get('chain',{}).get('contracts',[]) if r.get('contract',{}).get('symbol')==symbol]
    if len(rows) != 1 or rows[0]['quote']['symbol'] != symbol:
        raise ValueError('missing_or_ambiguous_quote')
    ct = rows[0]['contract']
    if ct['underlying'] not in cfg['universe']:
        raise ValueError('contract_identity')
    contract_valid(ct, ct['underlying'], at, cfg)
    return quote(rows[0]['quote'], at, cfg)


def mark(s, packet, at, cfg):
    s['unknown_mark'] = False
    value = 0
    if s['position']:
        value = -cfg['fee_per_contract_cents']
        try:
            bid,_,size,_,_ = find_quote(packet,s['position']['contract']['symbol'],at,cfg)
            if size < 1:
                raise ValueError('no_bid_liquidity')
            value = max(0,bid-cfg['exit_slippage_cents'])*100-cfg['fee_per_contract_cents']
        except (KeyError,TypeError,ValueError,AttributeError):
            s['unknown_mark'] = True
        s['position']['risk_mark_cents'] = value
        s['position']['mark_cents'] = None if s['unknown_mark'] else value
    s['equity_cents'] = s['cash_cents'] + value
    s['peak_cents'] = max(s['peak_cents'],s['equity_cents'])
    dd = s['peak_cents'] - s['equity_cents']
    s['max_drawdown_cents'] = max(s['max_drawdown_cents'],dd)
    s['daily_pause'] |= s['day_start_cents'] - s['equity_cents'] >= cfg['daily_pause_cents']
    s['experiment_pause'] |= dd >= cfg['drawdown_pause_cents']


def fill_quantity(requested, available):
    """One whole contract has only zero/full fills; fractional reports are invalid."""
    if integer(requested,1) != 1:
        raise ValueError('quantity_must_be_one')
    return min(1,integer(available))


def manage(s, packet, at, cfg):
    actions=[]
    day=at.astimezone(ET).date().isoformat()
    if s['day'] != day:
        s['day'],s['day_start_cents'],s['daily_pause'] = day,s['equity_cents'],False
    pos=s['position']
    if pos:
        try:
            closing = session_close(packet, at, cfg, require_open=False)
            pos['close_at'] = min(stamp(pos['close_at']), closing).isoformat()
        except (KeyError, TypeError, ValueError, AttributeError):
            pass  # Retain the known deadline; missing references never extend it.
    if pos and at >= stamp(pos['expiry_at']):
        # Explicit worst-case DNE lapse. No invented option quote or stock delivery.
        s['realized_cents'] -= pos['debit_cents']
        s['closed_trades'] += 1
        s['breaches'].append({'at':at.isoformat(),'reason':'unclosed_at_expiry_DNE_lapse','forfeited_intrinsic':'unknown'})
        s['position'],s['pending']=None,None
        actions.append({'kind':'expiry_lapse','value_cents':0,'policy':'simulated_DNE'})
    pending=s['pending']
    if pending:
        elapsed=(at-stamp(pending['decided_at'])).total_seconds()
        try:
            if pending['side']=='buy' and elapsed>cfg['ioc_timeout_seconds']:
                raise ValueError('ioc_timeout')
            session_close(packet, at, cfg)
            bid,ask,bs,az,qt=find_quote(packet,pending['contract']['symbol'],at,cfg)
            if qt <= stamp(pending['decided_at']) or elapsed<cfg['fill_latency_seconds']:
                raise ValueError('no_later_quote')
            if pending['side']=='buy':
                # Revalidate all non-agent entry constraints at the actual fill observation.
                candidate, reason, _ = select(packet,at,cfg)
                if candidate is None:
                    raise ValueError(reason)
                if pending['contract']['symbol'] != candidate['contract']['symbol']:
                    raise ValueError('candidate_changed')
                mark(s,packet,at,cfg)
                if s['daily_pause'] or s['experiment_pause'] or s['unknown_mark']:
                    raise ValueError('entry_pause')
                paid=ask+cfg['entry_slippage_cents']
                debit=paid*100+cfg['fee_per_contract_cents']
                if paid>pending['limit_cents'] or debit+cfg['fee_per_contract_cents']>cfg['max_contractual_loss_cents'] or debit>s['cash_cents']:
                    raise ValueError('entry_limit_or_risk')
                if not fill_quantity(1,az):
                    raise ValueError('unfilled_no_size')
                expiry=min(stamp(pending['contract']['expiry_at']),stamp(candidate['contract']['expiry_at']))
                s['position']={'contract':pending['contract'],'entry_cents':paid,'debit_cents':debit,
                               'opened_at':at.isoformat(),'close_at':min(stamp(pending['close_at']),stamp(candidate['close_at'])).isoformat(),
                               'expiry_at':expiry.isoformat(),'quantity':1,'exercise_policy':'simulated_DNE',
                               'decision_id':pending['decision_id']}
                s['cash_cents']-=debit
                s['spread_cents']+=(ask-bid)*100
                s['slippage_cents']+=cfg['entry_slippage_cents']*100
            else:
                if not fill_quantity(1,bs):
                    raise ValueError('unfilled_no_size')
                paid=max(0,bid-cfg['exit_slippage_cents'])
                # At zero recovery the fee is still an incurred cash cost.
                credit=paid*100-cfg['fee_per_contract_cents']
                s['cash_cents']+=credit
                s['realized_cents']+=credit-s['position']['debit_cents']
                s['position']=None
                s['closed_trades']+=1
                s['slippage_cents']+=(bid-paid)*100
            s['fees_cents']+=cfg['fee_per_contract_cents']
            s['fills']+=1
            actions.append({'kind':'simulated_fill','side':pending['side'],'price_cents':paid,'quantity':1,
                            'decision_id':pending['decision_id'],'quote_at':qt.isoformat()})
            s['pending']=None
        except (KeyError,TypeError,ValueError,AttributeError) as exc:
            actions.append({'kind':'unfilled','side':pending['side'],'reason':str(exc) if isinstance(exc,ValueError) else 'missing_data'})
            if pending['side']=='buy':
                s['pending']=None
    mark(s,packet,at,cfg)
    pos=s['position']
    if pos and not s['pending']:
        reason=None
        if at >= stamp(pos['close_at'])-timedelta(minutes=cfg['close_buffer_minutes']):
            reason='session_exit'
        elif at-stamp(pos['opened_at'])>=timedelta(minutes=cfg['max_hold_minutes']):
            reason='holding_limit'
        elif not s['unknown_mark']:
            bid,_,_,_,_=find_quote(packet,pos['contract']['symbol'],at,cfg)
            if bid*10000 <= pos['entry_cents']*(10000-cfg['stop_loss_bps']):
                reason='stop_loss'
            elif bid*10000 >= pos['entry_cents']*(10000+cfg['take_profit_bps']):
                reason='take_profit'
        if reason:
            s['pending']={'side':'sell','contract':pos['contract'],'decided_at':at.isoformat(),
                          'decision_id':digest([packet['event_id'],'exit',pos['decision_id']]),'reason':reason}
            actions.append({'kind':'exit_decision',**s['pending']})
    return actions


class Ledger:
    def __init__(self, path, kind='fixture'):
        self.cfg=config()
        if kind not in ('fixture','observed'):
            raise ValueError('invalid_evidence_kind')
        self.kind=kind
        path=require_no_symlink_components(path,label='shadow ledger')
        path.parent.mkdir(parents=True,exist_ok=True)
        for suffix in ('','-wal','-shm','-journal'):
            require_no_symlink_components(str(path)+suffix,label='shadow ledger')
        self.db=sqlite3.connect(path,timeout=30,isolation_level=None)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY,event_id TEXT UNIQUE NOT NULL,
        body TEXT NOT NULL,prev TEXT NOT NULL,hash TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS no_event_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;
        CREATE TRIGGER IF NOT EXISTS no_event_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;''')
        binding=canonical({'kind':kind,'freeze':digest(json.loads((ROOT/'FREEZE.json').read_text())),
                           'engine_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        with self.transaction():
            self.db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)',('binding',binding))
            if self.db.execute('SELECT value FROM meta WHERE key=?',('binding',)).fetchone()[0]!=binding:
                raise ValueError('ledger_version_or_kind_mismatch')

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def iter_history(self):
        prev='0'*64
        expected_seq=1
        for seq,eid,body,parent,h in self.db.execute('SELECT * FROM events ORDER BY seq'):
            if seq!=expected_seq or parent!=prev or digest([eid,body,parent])!=h:
                raise ValueError('ledger_integrity_failed')
            yield json.loads(body)
            expected_seq+=1
            prev=h

    def history(self):
        return list(self.iter_history())

    def latest_verified(self):
        last=None
        for last in self.iter_history():
            pass
        return last

    def state(self):
        last=self.latest_verified()
        return last['state'] if last else initial(self.cfg)

    def step(self, packet, proposals=None, *, now=None):
        config()  # Do not allow a long-lived process to ignore an edited freeze.
        if not isinstance(packet, dict):
            raise ValueError('invalid_envelope')
        if proposals is not None and not isinstance(proposals, dict):
            raise ValueError('invalid_proposal_container')
        at=stamp(packet['observed_at'])
        if packet['kind']!=self.kind or not isinstance(packet['event_id'],str) or not packet['event_id']:
            raise ValueError('invalid_envelope')
        if self.kind=='observed' and not 0 <= ((now or datetime.now(timezone.utc))-at).total_seconds() <= 60:
            raise ValueError('observed_packet_not_current')
        if self.kind == 'observed':
            self.reject_synthetic(packet)
        ph=digest(packet)
        supplied=proposals or {}
        if set(supplied)-{'analyst','critic'}:
            raise ValueError('unknown_proposal_role')
        with self.transaction():
            last=self.latest_verified()
            existing=self.db.execute('SELECT body FROM events WHERE event_id=?',(packet['event_id'],)).fetchone()
            if existing:
                old=json.loads(existing[0])
                if old['packet_hash']!=ph or old['supplied_proposals']!=supplied:
                    raise ValueError('conflicting_duplicate_event')
                return old
            if last and at<=stamp(last['observed_at']):
                raise ValueError('out_of_order_event')
            state=last['state'] if last else initial(self.cfg)
            decisions={}
            candidate,reason,contract_rejections=select(packet,at,self.cfg)
            analyst=supplied.get('analyst',mock_proposal('analyst',ph))
            critic=supplied.get('critic',mock_proposal('critic',ph))
            for arm,s in state.items():
                actions=manage(s,packet,at,self.cfg)
                verdict=reason
                proposal=None
                if candidate:
                    if s['position'] or s['pending']:
                        verdict='existing_exposure'
                    elif s['daily_pause'] or s['experiment_pause'] or s['unknown_mark']:
                        verdict='entry_pause'
                    else:
                        try:
                            accept=True
                            if arm!='deterministic':
                                proposal={'analyst':analyst}
                                accept=validate_proposal(analyst,'analyst',ph)
                            if arm=='analyst_critic':
                                proposal['critic']=critic
                                accept=validate_proposal(critic,'critic',ph) and accept
                            verdict='accepted' if accept else 'agent_abstain_or_veto'
                        except (KeyError,TypeError,ValueError,AttributeError):
                            verdict='invalid_proposal'
                        if verdict=='accepted':
                            s['pending']={**candidate,'side':'buy','decided_at':at.isoformat(),
                                          'decision_id':digest([packet['event_id'],arm,ph])}
                decisions[arm]={'verdict':verdict,'proposal':proposal,'actions':actions}
            body={'event_id':packet['event_id'],'observed_at':at.isoformat(),'packet_hash':ph,'packet':packet,
                  'supplied_proposals':supplied,'candidate':candidate,'contract_rejections':contract_rejections,
                  'decisions':decisions,'state':state,'model_cost_cents':0,'evidence_kind':self.kind}
            encoded=canonical(body)
            parent=self.db.execute('SELECT hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
            prev=parent[0] if parent else '0'*64
            self.db.execute('INSERT INTO events(event_id,body,prev,hash) VALUES (?,?,?,?)',
                            (packet['event_id'],encoded,prev,digest([packet['event_id'],encoded,prev])))
            return body

    @staticmethod
    def reject_synthetic(value):
        if isinstance(value,dict):
            if 'provenance' in value:
                p=value['provenance']
                if not isinstance(p, dict) or not isinstance(p.get('source'), str) or not isinstance(p.get('feed'), str):
                    raise ValueError('invalid_provenance')
                if 'fixture' in p['source'].lower() or p['feed'].lower() in ('fixture-only','indicative'):
                    raise ValueError('non_market_evidence_in_observed_packet')
            for v in value.values(): Ledger.reject_synthetic(v)
        elif isinstance(value,list):
            for v in value: Ledger.reject_synthetic(v)

    def close(self):
        self.db.close()
