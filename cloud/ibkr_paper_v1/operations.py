"""Durable operational state and reports. Never sends broker orders."""
import hashlib
import json
import os
import smtplib
import sqlite3
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
RECIPIENT = 'pranavm1104@gmail.com'


def utcnow():
    return datetime.now(timezone.utc)


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS health (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, received_ns INTEGER NOT NULL,
        kind TEXT NOT NULL, payload TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS events_received ON events(received_ns);
      CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, subject TEXT NOT NULL,
        body TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL, error TEXT);
      CREATE TABLE IF NOT EXISTS connectivity_watch (id INTEGER PRIMARY KEY CHECK(id=1),
        payload TEXT NOT NULL);
    ''')
    return db


def write_health(db, health):
    value = dict(health, updated_at=utcnow().isoformat())
    with db:
        db.execute('INSERT OR REPLACE INTO health VALUES (1, ?)', (json.dumps(value),))


def read_health(db, now):
    row = db.execute('SELECT payload FROM health WHERE id=1').fetchone()
    if row is None:
        return {'status': 'NO_COLLECTOR_HEARTBEAT', 'orders_enabled': False}
    health = json.loads(row[0])
    age = (now - datetime.fromisoformat(health['updated_at'])).total_seconds()
    if age < 0 or age > 90:
        return {'status': 'STALE_COLLECTOR_HEARTBEAT', 'orders_enabled': False,
                'heartbeat_age_seconds': age}
    return health


def calendar_rows(folder, now):
    """Read the existing hash-verified US regular-session calendar; fail closed."""
    folder = Path(folder)
    index = json.loads((folder / 'latest.json').read_text())
    name = index['file']
    if Path(name).name != name:
        raise ValueError('unsafe_calendar_path')
    raw = (folder / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != index['sha256']:
        raise ValueError('calendar_hash_mismatch')
    snapshot = json.loads(raw)
    age = (now - datetime.fromisoformat(snapshot['fetched_at'].replace('Z', '+00:00'))).total_seconds()
    if not 0 <= age <= 7 * 86400:
        raise ValueError('calendar_stale')
    rows = snapshot['calendar']
    dates = [row['date'] for row in rows]
    if not dates or dates != sorted(set(dates)):
        raise ValueError('invalid_calendar')
    day = now.astimezone(NY).date().isoformat()
    if not dates[0] <= day <= dates[-1]:
        raise ValueError('calendar_out_of_range')
    return rows


def session_for(rows, now):
    day = now.astimezone(NY).date().isoformat()
    for row in rows:
        if row['date'] == day:
            start = datetime.fromisoformat(day + 'T' + row['open']).replace(tzinfo=NY)
            end = datetime.fromisoformat(day + 'T' + row['close']).replace(tzinfo=NY)
            if end <= start:
                raise ValueError('invalid_session')
            return start, end
    return None


def due_reports(rows, now):
    session = session_for(rows, now)
    if session is None:
        return []
    start, end = session
    # Expire a missed pre-market email when the session starts; do not send it at night.
    windows = [('pre', start-timedelta(minutes=15), start),
               ('post', end+timedelta(minutes=15), end+timedelta(hours=6))]
    return [(kind, start.date().isoformat(), start, end)
            for kind, due, expiry in windows if due <= now < expiry]


def report_body(db, kind, day, now, session=None, analysis=None, execution=None):
    h = read_health(db, now)
    start = datetime.fromisoformat(day).replace(tzinfo=NY)
    end = start + timedelta(days=1)
    counts = dict(db.execute('SELECT kind, COUNT(*) FROM events WHERE received_ns>=? '
        'AND received_ns<? GROUP BY kind', (int(start.timestamp()*1e9), int(end.timestamp()*1e9))))
    lines = ['MNQ paper research — ' + kind + ' report', 'Date: ' + day,
             'Generated (UTC): ' + now.isoformat(), '', 'Status: ' + h['status'],
             ('Broker orders: PAPER ONLY; supervisor status: '+execution['status']+'.'
              if execution is not None else 'Broker orders: DISABLED — collection and operational verification only.'),
             'Live trading: NOT AUTHORIZED.', 'Contract: MNQZ6 (December 2026).']
    if execution is not None:
        lines += ['Execution gate: '+execution.get('reason','No additional gate reason reported.'),
                  'New entries currently eligible: '+str(execution.get('orders_eligible',False))+'.']
    if session:
        a, b = session
        lines += ['Research session: ' + a.strftime('%H:%M') + '–' + b.strftime('%H:%M') + ' New York.',
                  'Entry window: 09:45–11:30 New York; planned time exit: noon.',
                  'Scheduled session length: ' + str(int((b-a).total_seconds()/60)) + ' minutes.']
        from cloud.ibkr_paper_v1.session_audit import audit_session
        audit = audit_session(db, day, a, b, now)
        lines += ['Observed session coverage: ' + audit['status'],
                  'Coverage issues: ' + (', '.join(audit['issues']) or 'none detected'),
                  'Trade minutes observed: ' + str(audit['trade_minutes']) + '/' + str(audit['expected_minutes']),
                  'Coverage checks do not prove exchange-feed completeness or executable fills.']
    analysis_lines=['Candidate signals: NOT YET EVALUATED by the hosted session analyzer.']
    if analysis is not None:
        analysis_lines=['Session analysis: '+analysis['status']+'.']
        if analysis.get('reason'):analysis_lines.append('Analysis reason: '+analysis['reason']+'.')
        count=analysis.get('candidate_signal_count')
        if analysis['status']=='CANDIDATE_SIGNALS_EVALUATED' and type(count) is int:
            analysis_lines.append('Candidate signals in the unapproved receipt-time study: '+str(count)+'.')
        else:analysis_lines.append('Candidate signal count: UNKNOWN — not a zero-signal result.')
        analysis_lines.append('Candidate signals are not broker trades or approved performance evidence.')
    lines += ['', 'Captured today: ' + str(counts.get('trade', 0)) + ' trade events, '
              + str(counts.get('quote', 0)) + ' quote events.',
              *analysis_lines,
              ('Strategy paper fills and P&L: '+execution.get('performance_summary','No reconciled strategy trades yet.')
               if execution is not None else 'Broker paper fills / P&L / drawdown: NOT YET MEASURED.'),
              ('Simulation comparison: recorded per qualifying strategy trade; model equivalence is not assumed.'
               if execution is not None else 'Simulation comparison: PENDING adapter and matched-stream validation.'), '',
              ('Next gate: complete preceding-session data and a qualifying signal that passes risk and margin checks.'
               if execution is not None else 'Next gate: full same-contract warmup and feed-adapter validation, then supervised paper order lifecycle checks.'),
              'Connection or process uptime alone is not evidence of profitability.',
              'If authentication expires, sign in to the cloud paper Gateway; '
              'do not open a competing local TWS/live data session.']
    return '\n'.join(lines) + '\n'


def execution_status(state,now):
    path=Path(state)/'execution-health.json'
    if not path.exists():return None
    try:
        h=json.loads(path.read_text())
        age=(now-datetime.fromisoformat(h['updated_at'])).total_seconds()
        if h.get('paper_only') is not True or h.get('live_trading_authorized') is not False:
            raise ValueError('execution_identity')
        if not 0<=age<=90:h=dict(h,status='STALE_EXECUTION_SUPERVISOR',orders_eligible=False)
        ledger=Path(state)/'strategy-ledger.sqlite'
        if ledger.exists():
            conn=sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True)
            try:
                cash,peak,paused=conn.execute('SELECT cash_cents,peak_cents,paused FROM portfolio').fetchone()
                trades=conn.execute("SELECT COUNT(*) FROM audit WHERE kind='ROUND_TRIP_RECONCILED'").fetchone()[0]
                unresolved=conn.execute("SELECT COUNT(*) FROM intents WHERE phase!='RECONCILED_FLAT'").fetchone()[0]
                h['performance_summary']=f'{trades} reconciled strategy trades; net realized P&L USD {(cash-500000)/100:.2f}. Forced plumbing tests excluded.'
                if unresolved:h['performance_summary']+=f' {unresolved} unreconciled attempt(s); their P&L is not established.'
                h['portfolio_paused']=paused
            finally:conn.close()
        return h
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):
        return {'status':'EXECUTION_STATUS_UNVERIFIED','orders_eligible':False}


def enqueue(db, key, subject, body, now):
    with db:
        db.execute('INSERT OR IGNORE INTO outbox(id,subject,body,state,updated_at) '
                   'VALUES(?,?,?,\'pending\',?)', (key,subject,body,now.isoformat()))


def deliver(db, key, credentials, now, smtp_factory=smtplib.SMTP_SSL):
    """Do not retry an ambiguous SMTP acceptance after a disconnect/crash."""
    user = credentials['user']
    if user != RECIPIENT or not credentials.get('password'):
        raise ValueError('unexpected_or_missing_mail_credentials')
    with db:
        changed = db.execute("UPDATE outbox SET state='sending',attempts=attempts+1,updated_at=? "
            "WHERE id=? AND state='pending'", (now.isoformat(),key)).rowcount
    if not changed:
        return False
    subject, body = db.execute('SELECT subject,body FROM outbox WHERE id=?',(key,)).fetchone()
    message = EmailMessage()
    message['From'] = user
    message['To'] = RECIPIENT
    message['Subject'] = subject
    message['Message-ID'] = '<' + hashlib.sha256(key.encode()).hexdigest() + '@paper-research.local>'
    message.set_content(body)
    sending = False
    try:
        with smtp_factory('smtp.gmail.com', 465, timeout=20, context=ssl.create_default_context()) as server:
            server.login(user, credentials['password'].replace(' ', ''))
            sending = True
            refused = server.send_message(message, from_addr=user, to_addrs=[RECIPIENT])
            if refused:
                raise RuntimeError('recipient_refused')
        state, error = 'accepted_by_smtp', None
    except Exception as exc:
        state = 'delivery_unknown' if sending else 'pending'
        error = type(exc).__name__
    with db:
        db.execute('UPDATE outbox SET state=?,error=?,updated_at=? WHERE id=?',
                   (state,error,now.isoformat(),key))
    return state == 'accepted_by_smtp'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('mail_redirect_refused')


def deliver_https(db,key,credentials,now,opener=None):
    """Fixed Resend endpoint and recipient; no raw account credentials in email."""
    if credentials.get('provider') != 'resend' or not credentials.get('api_key','').startswith('re_'):
        raise ValueError('invalid_resend_configuration')
    with db:
        changed=db.execute("UPDATE outbox SET state='sending',attempts=attempts+1,updated_at=? "
            "WHERE id=? AND state='pending' AND attempts<12",(now.isoformat(),key)).rowcount
    if not changed:
        return False
    subject,body=db.execute('SELECT subject,body FROM outbox WHERE id=?',(key,)).fetchone()
    payload=json.dumps({'from':'Paper research <onboarding@resend.dev>',
        'to':[RECIPIENT],'subject':subject,'text':body},sort_keys=True).encode()
    req=Request('https://api.resend.com/emails',data=payload,method='POST',headers={
        'Authorization':'Bearer '+credentials['api_key'], 'Content-Type':'application/json',
        'User-Agent':'mnq-paper-research/1.0',
        'Idempotency-Key':'paper-mnq-'+hashlib.sha256(key.encode()).hexdigest()})
    opener=opener or build_opener(ProxyHandler({}),NoRedirect())
    try:
        with opener.open(req,timeout=20) as response:
            reply=json.loads(response.read(16384))
            if not isinstance(reply.get('id'),str) or not reply['id']:
                raise ValueError('mail_receipt_missing')
        state,error='accepted_by_email_api',None
    except HTTPError as exc:
        state='pending' if exc.code == 429 or exc.code >= 500 else 'provider_rejected'
        error='HTTP_'+str(exc.code)
    except Exception as exc:
        # Safe to retry the identical request within this report's same-day window.
        state,error='pending',type(exc).__name__
    with db:
        db.execute('UPDATE outbox SET state=?,error=?,updated_at=? WHERE id=?',
                   (state,error,now.isoformat(),key))
    return state=='accepted_by_email_api'


def connectivity_watch(db, health, now, session=None):
    """Persist outage detection across reporter restarts, including overnight.

    This observes the collector's authenticated API checks. It cannot authenticate
    Gateway, prove fresh prices outside capture hours, or detect a dead host.
    """
    row=db.execute('SELECT payload FROM connectivity_watch WHERE id=1').fetchone()
    incident=json.loads(row[0]) if row else None
    active=session is not None and session[0]<=now<session[1]
    healthy=(health['status']=='COLLECTING_REALTIME' or
             (health['status']=='OUTSIDE_RESEARCH_SESSION' and not active))
    day=now.astimezone(NY).date().isoformat()
    if healthy:
        if incident is None:return
        if 'recovering_at' not in incident:
            incident['recovering_at']=now.isoformat()
        stable=(now-datetime.fromisoformat(incident['recovering_at'])).total_seconds()
        if stable>=120:
            # Unsent outage notices should not arrive after a confirmed recovery.
            key=incident.get('alert_key')
            notified=False
            if key:
                sent=db.execute('SELECT state FROM outbox WHERE id=?',(key,)).fetchone()
                notified=sent is not None and sent[0] in ('accepted_by_email_api','accepted_by_smtp','sending','delivery_unknown')
                with db:db.execute("UPDATE outbox SET state='expired' WHERE id=? AND state='pending'",(key,))
            if notified:
                enqueue(db,day+':connectivity-recovered:'+incident['started_at'],
                    '[PAPER MNQ] Gateway connection recovered',
                    'Collector API checks have remained healthy for two minutes.\n'
                    'Observed UTC: '+now.isoformat()+'\nStatus: '+health['status']+'\n'
                    'This confirms connection recovery only; session data, strategy and risk gates still apply.\n'
                    'Live trading is not authorized.\n',now)
            with db:db.execute('DELETE FROM connectivity_watch WHERE id=1')
            return
    else:
        if incident is None:incident={'started_at':now.isoformat()}
        incident.pop('recovering_at',None)
        age=(now-datetime.fromisoformat(incident['started_at'])).total_seconds()
        # Three minutes filters a routine restart; active-session failures retain
        # immediate reporting. Clock reversal restarts the observation interval.
        if age<0:incident={'started_at':now.isoformat()};age=0
        if age>=180 or active:
            key=day+':connectivity:'+incident['started_at']
            incident['alert_key']=key
            enqueue(db,key,'[PAPER MNQ] Gateway or collector needs attention',
                'Observed UTC: '+now.isoformat()+'\nFirst observed UTC: '+incident['started_at']+'\n'
                'Status: '+health['status']+'\n'
                'The collector cannot verify its required broker connection/data state.\n'
                'New strategy entries require healthy data and remain subject to all gates.\n'
                'Inspect the cloud paper Gateway; this status alone does not prove login expired.\n'
                'Do not start a competing local TWS session. Live trading is not authorized.\n',now)
    with db:
        db.execute('INSERT OR REPLACE INTO connectivity_watch VALUES (1,?)',(json.dumps(incident),))


def reporter_cycle(state_dir, references, credentials_path, now=None):
    now = now or utcnow()
    db = connect(Path(state_dir)/'state.sqlite')
    execution=execution_status(state_dir,now)
    try:
        rows = calendar_rows(references, now)
        for kind, day, start, end in due_reports(rows, now):
            from cloud.ibkr_paper_v1.session_analysis import load_result,revision
            try:
                analysis=load_result(state_dir,day)
                if analysis is not None and analysis.get('code_sha256')!=revision():
                    analysis={'status':'STALE_ANALYSIS','reason':'ANALYSIS_CODE_CHANGED'}
            except (OSError,ValueError,KeyError,TypeError):
                analysis={'status':'ANALYSIS_ERROR','reason':'RESULT_MISSING_OR_FAILED_INTEGRITY_CHECK'}
            enqueue(db, day+':'+kind, '[PAPER MNQ] '+day+' '+kind+'-session report',
                    report_body(db,kind,day,now,(start,end),analysis,execution),now)
        h = read_health(db,now)
        session = session_for(rows,now)
        day = now.astimezone(NY).date().isoformat()
        with db:
            db.execute("UPDATE outbox SET state='expired' WHERE state='pending' AND attempts=0 "
                "AND id LIKE ? AND id!=?",(day+':attention:%',day+':attention:'+h['status']))
        connectivity_watch(db,h,now,session)
        if execution and execution['status'] in ('ATTENTION_REQUIRED','STALE_EXECUTION_SUPERVISOR',
                                                 'EXECUTION_STATUS_UNVERIFIED','SUPERVISOR_STOPPED'):
            enqueue(db,day+':execution:'+execution['status'],'[PAPER MNQ] Execution needs attention',
                'Paper supervisor: '+execution['status']+'\nReason: '+execution.get('reason','Inspect the cloud execution journal.')+
                '\nNew entries are blocked. Existing native protection must be checked if a position remains.\nLive trading is not authorized.\n',now)
    except (OSError, ValueError, KeyError, TypeError):
        day = now.astimezone(NY).date().isoformat()
        enqueue(db,day+':calendar-error','[PAPER MNQ] Calendar needs attention',
                'The calendar is missing, stale, or invalid. Scheduled strategy activity '
                'is blocked; no orders are enabled. Please inspect the cloud service.\n',now)
    if Path(credentials_path).exists():
        credentials = json.loads(Path(credentials_path).read_text())
        # Bound catch-up and avoid sending stale session emails from prior dates.
        day = now.astimezone(NY).date().isoformat()
        with db:
            db.execute("UPDATE outbox SET state='expired' WHERE state='pending' AND id<?",(day,))
            if credentials.get('provider')=='resend':
                # The same-day bound keeps all recovery inside Resend's 24-hour
                # idempotency retention. systemd prevents concurrent invocations.
                db.execute("UPDATE outbox SET state='pending' WHERE state='sending' "
                    "AND id>=? AND updated_at<?",(day,(now-timedelta(seconds=120)).isoformat()))
            db.execute("UPDATE outbox SET state='retry_limit' WHERE state='pending' AND attempts>=12")
        # A pre-session message awaiting credentials must not arrive after the open.
        session=session_for(rows,now) if 'rows' in locals() else None
        if session and now >= session[0]:
            with db:
                db.execute("UPDATE outbox SET state='expired' WHERE id=? AND state='pending'",(day+':pre',))
        for (key,) in db.execute("SELECT id FROM outbox WHERE state='pending' AND attempts<12 ORDER BY id LIMIT 3").fetchall():
            if credentials.get('provider')=='resend':
                deliver_https(db,key,credentials,now)
            else:
                deliver(db,key,credentials,now)
    summary = dict(db.execute('SELECT state,COUNT(*) FROM outbox GROUP BY state'))
    db.close()
    return summary


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--state',default='/var/lib/ibkr-paper')
    parser.add_argument('--references',default='/var/lib/trading-collector/references')
    parser.add_argument('--credentials',default='/etc/ibkr-paper/smtp.json')
    args=parser.parse_args()
    print(json.dumps(reporter_cycle(args.state,args.references,args.credentials)))
