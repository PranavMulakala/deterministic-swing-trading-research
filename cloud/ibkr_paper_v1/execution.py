"""Durable paper-order planning and recovery primitives.

This module does not connect or transmit. The future broker adapter must reconcile
its records before dispatch. Native brackets are a distinct execution version,
not the historical model's delayed BBO-triggered market exits.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import sqlite3
from zoneinfo import ZoneInfo

from ibapi.order import Order

ACCOUNT = 'DUT109401'
SYMBOL = 'MNQZ6'
VERSION = 'ibkr_native_bracket_paper_v1_candidate'
NS = 1_000_000_000
NY = ZoneInfo('America/New_York')


def integer(value, low=0):
    if type(value) is not int or value < low:
        raise ValueError('invalid_integer')
    return value


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def plan(signal, quote, now_ns, fee_bound_cents, fee_source_sha256,
         entry_slippage_ticks=2, stop_slippage_ticks=2):
    """Worst planned entry at a limit; a stop-market loss remains unbounded.

    An externally verified fee ceiling is required. The source hash is provenance,
    not verification by itself. This function does not approve a data adapter.
    """
    integer(now_ns,1)
    integer(fee_bound_cents,1)
    integer(entry_slippage_ticks)
    integer(stop_slippage_ticks)
    if (not isinstance(fee_source_sha256,str) or len(fee_source_sha256)!=64
            or any(c not in '0123456789abcdef' for c in fee_source_sha256)):
        raise ValueError('fee_provenance_required')
    if signal.get('contract') != SYMBOL or quote.get('contract') != SYMBOL:
        raise ValueError('wrong_contract')
    if type(signal.get('direction')) is not int or signal['direction'] not in (-1,1):
        raise ValueError('wrong_direction')
    direction=signal['direction']
    signal_ns=integer(signal['signal_ns'],1)
    stamp=datetime.fromtimestamp(signal_ns//NS,timezone.utc).astimezone(NY)
    if not (9*60+45 <= stamp.hour*60+stamp.minute < 11*60+30):
        raise ValueError('signal_outside_entry_window')
    if not signal_ns+NS <= now_ns < signal_ns+2*NS:
        raise ValueError('entry_window_expired_or_early')
    if not isinstance(signal.get('id'),str) or not signal['id'] or len(signal['id'])>128:
        raise ValueError('invalid_signal_identity')
    received=integer(quote['received_ns'],1)
    if not 0 <= now_ns-received <= NS//4 or received < signal_ns+NS:
        raise ValueError('stale_or_predecision_quote')
    if type(quote.get('data_type')) is not int or quote['data_type'] != 1:
        raise ValueError('realtime_quote_required')
    bid,ask=integer(quote['bid_ticks'],1),integer(quote['ask_ticks'],1)
    integer(quote['bid_size'],1); integer(quote['ask_size'],1)
    if not 0 <= ask-bid <= 4:
        raise ValueError('invalid_or_wide_book')
    entry=(ask+entry_slippage_ticks if direction==1 else bid-entry_slippage_ticks)
    stop=integer(signal['stop_ticks'],1)
    target=integer(signal['target_ticks'],1)
    distance=direction*(entry-stop)
    reward_distance=direction*(target-entry)
    if distance<=0 or reward_distance<=0:
        raise ValueError('stop_or_target_already_passed')
    risk=(distance+stop_slippage_ticks)*50+fee_bound_cents
    reward=reward_distance*50-fee_bound_cents
    if risk>1250 or reward*2 < risk*3:
        raise ValueError('risk_or_reward_gate')
    return {'version':VERSION,'signal_id':signal['id'],'day':stamp.date().isoformat(),
            'account':ACCOUNT,'contract':SYMBOL,'direction':direction,'quantity':1,
            'signal_ns':signal_ns,'planned_at_ns':now_ns,'expires_ns':signal_ns+2*NS,
            'entry_ticks':entry,'stop_ticks':stop,'target_ticks':target,
            'planned_risk_cents':risk,'planned_reward_cents':reward,
            'fee_bound_cents':fee_bound_cents,'fee_source_sha256':fee_source_sha256,
            'stop_slippage_ticks':stop_slippage_ticks,'quote':dict(quote),
            'loss_limit_guaranteed':False}


def bracket_orders(value, first_id):
    """Build official SDK orders; deliberately no EClient or network call here."""
    integer(first_id,1)
    if value.get('version')!=VERSION or value.get('account')!=ACCOUNT or value.get('contract')!=SYMBOL:
        raise ValueError('unrecognized_plan')
    if value.get('quantity')!=1 or type(value['quantity']) is not int:
        raise ValueError('one_contract_only')
    if type(value.get('direction')) is not int or value['direction'] not in (-1,1):
        raise ValueError('wrong_direction')
    for key in ('entry_ticks','stop_ticks','target_ticks','expires_ns'):
        integer(value[key],1)
    if not (value['direction']*(value['entry_ticks']-value['stop_ticks'])>0
            and value['direction']*(value['target_ticks']-value['entry_ticks'])>0):
        raise ValueError('invalid_bracket_prices')
    action='BUY' if value['direction']==1 else 'SELL'
    opposite='SELL' if action=='BUY' else 'BUY'
    reference='pm-'+hashlib.sha256(value['signal_id'].encode()).hexdigest()[:24]
    orders=[]
    for offset,leg in enumerate(('entry','target','stop')):
        order=Order()
        order.orderId=first_id+offset
        order.account=ACCOUNT
        order.orderRef=reference+'-'+leg
        order.action=action if leg=='entry' else opposite
        order.totalQuantity=Decimal(1)
        order.orderType='STP' if leg=='stop' else 'LMT'
        order.transmit=(leg=='stop')
        order.parentId=0 if leg=='entry' else first_id
        order.tif='GTD' if leg=='entry' else 'GTC'
        order.outsideRth=False
        order.overridePercentageConstraints=False
        if leg=='entry':
            order.lmtPrice=value['entry_ticks']/4
            order.goodTillDate=datetime.fromtimestamp(value['expires_ns']//NS,timezone.utc).strftime('%Y%m%d %H:%M:%S UTC')
        elif leg=='target':
            order.lmtPrice=value['target_ticks']/4
        else:
            order.auxPrice=value['stop_ticks']/4
            order.triggerMethod=2  # Last, as defined by the official SDK.
        orders.append(order)
    return orders


class Ledger:
    """One-contract paper sub-ledger, persisted before any external submission.

    It intentionally cannot clear an ambiguous submission or a pause automatically.
    Broker reconciliation and explicit reviewed recovery are separate operations.
    """
    def __init__(self,path):
        self.session_next={}
        self.db=sqlite3.connect(path,timeout=10,isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS portfolio(id INTEGER PRIMARY KEY CHECK(id=1),
            cash_cents INTEGER,peak_cents INTEGER,paused TEXT);
          INSERT OR IGNORE INTO portfolio VALUES(1,500000,500000,NULL);
          CREATE TABLE IF NOT EXISTS days(day TEXT PRIMARY KEY,start_cents INTEGER,attempts INTEGER,paused TEXT);
          CREATE TABLE IF NOT EXISTS intents(signal_id TEXT PRIMARY KEY,day TEXT,
            phase TEXT,plan TEXT,plan_hash TEXT,first_order_id INTEGER UNIQUE);
          CREATE TABLE IF NOT EXISTS dispatch(order_id INTEGER PRIMARY KEY,signal_id TEXT,leg TEXT,
            state TEXT,UNIQUE(signal_id,leg));
          CREATE TABLE IF NOT EXISTS fills(exec_id TEXT PRIMARY KEY,signal_id TEXT,leg TEXT,
            price_ticks INTEGER,fee_cents INTEGER,payload TEXT);
          CREATE TABLE IF NOT EXISTS order_status(order_id INTEGER PRIMARY KEY,status TEXT,
            filled INTEGER,remaining INTEGER,perm_id INTEGER,receipt_ns INTEGER);
          CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,kind TEXT,payload TEXT);
        ''')

    @contextmanager
    def atomic(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def reserve(self,value,first_order_id,now_ns):
        if value.get('account')!=ACCOUNT or value.get('version')!=VERSION:
            raise ValueError('paper_plan_required')
        integer(first_order_id,1)
        if not value['planned_at_ns'] <= now_ns < value['expires_ns']:
            raise ValueError('plan_expired')
        # Recompute from original signal and quote, preventing edited risk/price
        # fields from bypassing the gate between planning and reservation.
        source={'id':value['signal_id'],'contract':value['contract'],
                'direction':value['direction'],'signal_ns':value['signal_ns'],
                'stop_ticks':value['stop_ticks'],'target_ticks':value['target_ticks']}
        q=value['quote']
        slip=abs(value['entry_ticks']-(q['ask_ticks'] if value['direction']==1 else q['bid_ticks']))
        checked=plan(source,q,value['planned_at_ns'],value['fee_bound_cents'],
                     value['fee_source_sha256'],slip,value['stop_slippage_ticks'])
        if canonical(checked)!=canonical(value):
            raise ValueError('plan_modified')
        # The quote must still be fresh at reservation, not merely at planning.
        if not 0<=now_ns-q['received_ns']<=NS//4:
            raise ValueError('quote_expired_before_reservation')
        encoded=canonical(value)
        with self.atomic():
            if self.db.execute('SELECT 1 FROM intents WHERE signal_id=?',(value['signal_id'],)).fetchone():
                raise ValueError('signal_already_reserved_never_resubmit')
            if self.db.execute("SELECT 1 FROM intents WHERE phase!='RECONCILED_FLAT'").fetchone():
                raise ValueError('prior_intent_requires_reconciliation')
            cash,peak,paused=self.db.execute('SELECT cash_cents,peak_cents,paused FROM portfolio').fetchone()
            if paused: raise ValueError('portfolio_paused')
            self.db.execute('INSERT OR IGNORE INTO days VALUES(?,?,0,NULL)',(value['day'],cash))
            day_start,attempts,day_pause=self.db.execute('SELECT start_cents,attempts,paused FROM days WHERE day=?',(value['day'],)).fetchone()
            if day_pause or attempts>=2: raise ValueError('daily_pause_or_attempt_limit')
            if value['planned_risk_cents']>min(1250,day_start//400):
                raise ValueError('equity_adjusted_risk_gate')
            self.db.execute('INSERT INTO intents VALUES(?,?,?,?,?,?)',
                (value['signal_id'],value['day'],'RESERVED',encoded,hashlib.sha256(encoded.encode()).hexdigest(),first_order_id))
            for i,leg in enumerate(('entry','target','stop')):
                self.db.execute('INSERT INTO dispatch VALUES(?,?,?,?)',(first_order_id+i,value['signal_id'],leg,'UNSENT'))
            self.db.execute('UPDATE days SET attempts=attempts+1 WHERE day=?',(value['day'],))
        self.session_next[value['signal_id']]=first_order_id

    def before_send(self,order_id):
        """Durably mark uncertainty BEFORE touching the broker socket, once only."""
        with self.atomic():
            row=self.db.execute('SELECT signal_id,state FROM dispatch WHERE order_id=?',(order_id,)).fetchone()
            if row is None or row[1]!='UNSENT': raise ValueError('dispatch_not_retryable')
            if self.session_next.get(row[0])!=order_id:
                raise ValueError('restart_or_out_of_order_dispatch_requires_reconciliation')
            self.db.execute("UPDATE dispatch SET state='SUBMISSION_UNKNOWN' WHERE order_id=?",(order_id,))
            self.db.execute("UPDATE intents SET phase='RECONCILIATION_REQUIRED' WHERE signal_id=?",(row[0],))
        self.session_next[row[0]]=order_id+1

    def transport_failed(self,signal_id):
        self.session_next.pop(signal_id,None)
        with self.atomic():
            self.db.execute('INSERT INTO audit(kind,payload) VALUES(?,?)',
                            ('TRANSPORT_FAILED',canonical({'signal_id':signal_id})))

    def record_fill(self,exec_id,signal_id,leg,price_ticks,fee_cents,raw):
        if not isinstance(exec_id,str) or not exec_id or leg not in ('entry','target','stop','time_exit'):
            raise ValueError('invalid_fill_identity')
        integer(price_ticks,1)
        if fee_cents is not None: integer(fee_cents)
        payload=canonical(raw)
        value=(signal_id,leg,price_ticks,fee_cents,payload)
        with self.atomic():
            row=self.db.execute('SELECT plan FROM intents WHERE signal_id=?',(signal_id,)).fetchone()
            if row is None:
                raise ValueError('unowned_execution')
            planned=json.loads(row[0])
            expected_side='BUY' if planned['direction']==1 else 'SELL'
            if leg!='entry': expected_side='SELL' if expected_side=='BUY' else 'BUY'
            if (raw.get('account')!=ACCOUNT or raw.get('contract')!=SYMBOL
                    or type(raw.get('quantity')) is not int or raw['quantity']!=1
                    or raw.get('side')!=expected_side
                    or not self.db.execute('SELECT 1 FROM dispatch WHERE order_id=? AND signal_id=? AND leg=?',
                                           (raw.get('order_id'),signal_id,leg)).fetchone()):
                raise ValueError('execution_does_not_match_owned_order')
            old=self.db.execute('SELECT signal_id,leg,price_ticks,fee_cents,payload FROM fills WHERE exec_id=?',(exec_id,)).fetchone()
            if old is not None:
                if old[:3]!=value[:3] or old[4]!=payload or (fee_cents is not None and old[3] not in (None,fee_cents)):
                    raise ValueError('execution_correction_requires_review')
                if old[3] is None and fee_cents is not None:
                    self.db.execute('UPDATE fills SET fee_cents=? WHERE exec_id=?',(fee_cents,exec_id))
                return False
            self.db.execute('INSERT INTO fills VALUES(?,?,?,?,?,?)',(exec_id,*value[:4],payload))
        return True

    def record_order_status(self,order_id,status,filled,remaining,perm_id,receipt_ns):
        if status not in ('ApiPending','PendingSubmit','PreSubmitted','Submitted',
                          'PendingCancel','Cancelled','ApiCancelled','Filled','Inactive'):
            raise ValueError('unknown_order_status')
        integer(filled);integer(remaining);integer(perm_id);integer(receipt_ns,1)
        if filled+remaining>1: raise ValueError('unexpected_broker_quantity')
        with self.atomic():
            if not self.db.execute('SELECT 1 FROM dispatch WHERE order_id=?',(order_id,)).fetchone():
                raise ValueError('unowned_order_status')
            old=self.db.execute('SELECT filled,receipt_ns FROM order_status WHERE order_id=?',(order_id,)).fetchone()
            if old and (filled<old[0] or receipt_ns<old[1]):
                raise ValueError('out_of_order_broker_status_requires_review')
            self.db.execute('INSERT OR REPLACE INTO order_status VALUES(?,?,?,?,?,?)',
                            (order_id,status,filled,remaining,perm_id,receipt_ns))

    def reconcile_cancelled_unfilled(self,signal_id,position,owned_open_orders,complete_snapshot):
        if type(position) is not int or position!=0 or owned_open_orders or complete_snapshot is not True:
            raise ValueError('broker_flat_not_reconciled')
        with self.atomic():
            row=self.db.execute('SELECT phase FROM intents WHERE signal_id=?',(signal_id,)).fetchone()
            if row is None: raise ValueError('unknown_intent')
            if row[0]=='RECONCILED_FLAT': return False
            if self.db.execute('SELECT 1 FROM fills WHERE signal_id=?',(signal_id,)).fetchone():
                raise ValueError('executions_require_pnl_reconciliation')
            states=self.db.execute('SELECT s.status,s.filled FROM dispatch d LEFT JOIN order_status s '
                                   'ON s.order_id=d.order_id WHERE d.signal_id=?',(signal_id,)).fetchall()
            if len(states)!=3 or any(s not in ('Cancelled','ApiCancelled') or q!=0 for s,q in states):
                raise ValueError('terminal_cancellation_evidence_required')
            self.db.execute("UPDATE intents SET phase='RECONCILED_FLAT' WHERE signal_id=?",(signal_id,))
            self.db.execute('INSERT INTO audit(kind,payload) VALUES(?,?)',
                            ('UNFILLED_CANCELLED_RECONCILED',canonical({'signal_id':signal_id})))
        self.session_next.pop(signal_id,None)
        return True

    def mark_position(self,signal_id,quote,now_ns):
        """Persist unrealized loss/peak pauses; the supervisor owns exit actions.

        This does not pretend a quote is an executable fill or place a competing
        close order alongside a native stop. Missing data requires protection
        verification and reconciliation, not a guessed flat position.
        """
        integer(now_ns,1)
        with self.atomic():
            row=self.db.execute('SELECT day,phase,plan FROM intents WHERE signal_id=?',(signal_id,)).fetchone()
            if row is None:raise ValueError('unknown_intent')
            day,phase,encoded=row
            if phase=='RECONCILED_FLAT':return {'action':'NONE','position':'RECONCILED_FLAT'}
            fills=self.db.execute('SELECT leg,price_ticks FROM fills WHERE signal_id=?',(signal_id,)).fetchall()
            entries=[x for x in fills if x[0]=='entry'];exits=[x for x in fills if x[0]!='entry']
            if not entries and not exits:return {'action':'RECONCILE_PENDING_ENTRY','position':'UNCONFIRMED'}
            if len(entries)==1 and len(exits)==1:return {'action':'RECONCILE_FLAT','position':'UNCONFIRMED'}
            problem=None
            if len(entries)!=1 or exits:problem='UNEXPECTED_POSITION_LEDGER'
            try:
                integer(quote['received_ns'],1)
                bid,ask=integer(quote['bid_ticks'],1),integer(quote['ask_ticks'],1)
                integer(quote['bid_size'],1);integer(quote['ask_size'],1)
                if (quote.get('contract')!=SYMBOL or type(quote.get('data_type')) is not int
                        or quote['data_type']!=1 or bid>ask
                        or not 0<=now_ns-quote['received_ns']<=NS):
                    problem=problem or 'DATA_QUALITY_PAUSE'
            except (KeyError,ValueError,TypeError):problem=problem or 'DATA_QUALITY_PAUSE'
            cash,peak,paused=self.db.execute('SELECT cash_cents,peak_cents,paused FROM portfolio').fetchone()
            if problem:
                self.db.execute('UPDATE portfolio SET paused=?',(paused or problem,))
                result={'action':'VERIFY_PROTECTION_AND_RECONCILE','position':'UNRESOLVED',
                        'marked_equity_cents':None,'reason':problem}
                self.db.execute('INSERT INTO audit(kind,payload) VALUES(?,?)',
                    ('RISK_MARK_BLOCKED',canonical(dict(result,signal_id=signal_id,at_ns=now_ns))))
                return result
            value=json.loads(encoded)
            liquidation=bid if value['direction']==1 else ask
            marked=cash+value['direction']*(liquidation-entries[0][1])*50-value['fee_bound_cents']
            peak=max(peak,marked)
            if (peak-marked)*20>=peak:paused=paused or 'HIGH_WATER_DRAWDOWN'
            self.db.execute('UPDATE portfolio SET peak_cents=?,paused=?',(peak,paused))
            opening,day_pause=self.db.execute('SELECT start_cents,paused FROM days WHERE day=?',(day,)).fetchone()
            if opening-marked>=min(2500,opening//200):
                day_pause=day_pause or 'DAILY_LOSS'
                self.db.execute('UPDATE days SET paused=? WHERE day=?',(day_pause,day))
            result={'action':'CLOSE_REQUIRED_WITHOUT_DUPLICATE_EXIT' if paused or day_pause else 'MONITOR',
                    'marked_equity_cents':marked,'unrealized_peak_cents':peak,
                    'portfolio_pause':paused,'day_pause':day_pause,
                    'fee_reserve_cents':value['fee_bound_cents'],'quote_is_guaranteed_fill':False}
            self.db.execute('INSERT INTO audit(kind,payload) VALUES(?,?)',('RISK_MARK',canonical(dict(result,signal_id=signal_id,at_ns=now_ns))))
        return result

    def reconcile_flat(self,signal_id,position,owned_open_orders,complete_snapshot,
                       fees_by_execution):
        """Use complete fresh broker callbacks, not a caller-invented empty list.

        The adapter must validate account, timestamps, request-end markers and
        commissions before invoking this primitive. No automatic recovery sender.
        """
        if type(position) is not int or position!=0 or owned_open_orders or complete_snapshot is not True:
            raise ValueError('broker_flat_not_reconciled')
        with self.atomic():
            row=self.db.execute('SELECT day,phase,plan FROM intents WHERE signal_id=?',(signal_id,)).fetchone()
            if row is None: raise ValueError('unknown_intent')
            day,phase,encoded=row
            if phase=='RECONCILED_FLAT': return False
            fills=self.db.execute('SELECT exec_id,leg,price_ticks,fee_cents FROM fills WHERE signal_id=?',(signal_id,)).fetchall()
            entries=[x for x in fills if x[1]=='entry']
            exits=[x for x in fills if x[1]!='entry']
            if not fills:
                # An absence of recent executions cannot disambiguate an order
                # beyond the broker query's retention window. Retain the block.
                raise ValueError('unfilled_intent_needs_terminal_order_evidence')
            if len(entries)!=1 or len(exits)!=1: raise ValueError('one_entry_one_exit_required')
            fees=0
            for execution,leg,price,fee in fills:
                resolved=fees_by_execution.get(execution,fee)
                if resolved is None: raise ValueError('missing_commission')
                integer(resolved)
                if fee is not None and fee!=resolved: raise ValueError('conflicting_commission')
                fees+=resolved
                self.db.execute('UPDATE fills SET fee_cents=? WHERE exec_id=?',(resolved,execution))
            value=json.loads(encoded)
            pnl=value['direction']*(exits[0][2]-entries[0][2])*50-fees
            cash,peak,paused=self.db.execute('SELECT cash_cents,peak_cents,paused FROM portfolio').fetchone()
            cash+=pnl; peak=max(cash,peak)
            if (peak-cash)*20>=peak: paused='HIGH_WATER_DRAWDOWN'
            self.db.execute('UPDATE portfolio SET cash_cents=?,peak_cents=?,paused=?',(cash,peak,paused))
            opening=self.db.execute('SELECT start_cents FROM days WHERE day=?',(day,)).fetchone()[0]
            if opening-cash>=min(2500,opening//200):
                self.db.execute("UPDATE days SET paused='DAILY_LOSS' WHERE day=?",(day,))
            self.db.execute("UPDATE intents SET phase='RECONCILED_FLAT' WHERE signal_id=?",(signal_id,))
            self.db.execute('INSERT INTO audit(kind,payload) VALUES(?,?)',('ROUND_TRIP_RECONCILED',canonical({'signal_id':signal_id,'pnl_cents':pnl})))
        return True

    def close(self):
        self.db.close()
