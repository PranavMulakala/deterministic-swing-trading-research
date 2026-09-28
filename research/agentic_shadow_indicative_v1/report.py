"""Readable, escaped local report with unknown marks kept distinct from risk marks."""
from collections import Counter, deque
from .engine import ARMS, initial
from html import escape
import json
from datetime import datetime, timezone


def build(ledger):
    latest=None
    recent=deque(maxlen=20)
    count=0
    reasons={arm:Counter() for arm in ARMS}
    unfilled={arm:Counter() for arm in ARMS}
    rejections=Counter()
    for row in ledger.iter_history():
        latest=row
        count+=1
        rejections.update(row['contract_rejections'])
        for arm in ARMS:
            reasons[arm][row['decisions'][arm]['verdict']]+=1
            unfilled[arm].update(a['reason'] for a in row['decisions'][arm]['actions'] if a['kind']=='unfilled')
        recent.append({k:row[k] for k in ('event_id','observed_at','packet_hash','candidate','decisions')})
    arms={}
    state=latest['state'] if latest else initial(ledger.cfg)
    for name,s in state.items():
        pos=s['position']
        arms[name]={**s,'unrealized_cents':None if pos and s['unknown_mark'] else (pos['mark_cents']-pos['debit_cents'] if pos else 0),
                    'net_pnl_cents':s['equity_cents']-750000,'decision_reasons':dict(reasons[name]),
                    'unfilled_reasons':dict(unfilled[name])}
    complete_packet = bool(latest and all(key in latest['packet'] for key in
                           ('chain','underlying','bars','calendar','events','news')))
    pipeline_status = (
        'INDICATIVE PIPELINE ONLY: modified/delayed data cannot validate the OPRA hypothesis'
        if ledger.kind == 'indicative' and complete_packet
        else 'BLOCKED: no complete current Alpaca indicative packet has been accepted'
    )
    return {'experiment':ledger.cfg['experiment'],'capital_per_arm_cents':750000,'evidence_kind':ledger.kind,
            'purpose':'PLUMBING ONLY',
            'execution_validity':'NOT VALID FOR PROFIT, EXECUTION, OR AGENT-EFFICACY ANALYSIS',
            'local_software':'see README.md and evidence for tested release verdict',
            'real_data_readiness':pipeline_status,
            'real_money':'DISABLED; no broker order client or endpoint','model':'mock-v1; zero API calls',
            'costs_note':'Fees are debited. Spread/slippage figures are attribution, not additional debits. External data/cloud costs unverified.',
            'unknown_marks_note':'Unknown liquidation marks use worst-case loss plus reserved exit fee for risk decisions; these are not observed prices.',
            'generated_at':datetime.now(timezone.utc).isoformat(),'last_observation':latest['observed_at'] if latest else None,
            'observations':count,'available_data':{k:bool(latest and k in latest['packet']) for k in ('chain','underlying','bars','calendar','events','news')},
            'contract_rejections':dict(rejections),
            'arms':arms,'last_decisions':latest['decisions'] if latest else {},
            'recent_decisions':list(recent),
            'sources':{k:{f:(latest['packet'][k].get('provenance') if isinstance(latest['packet'][k].get('provenance'),dict) else {}).get(f) for f in ('source','feed','published_at','received_at')}
                       for k in ('chain','underlying','calendar','events','news') if latest and isinstance(latest['packet'].get(k),dict)},
            'interpretation':'PLUMBING ONLY. Do not interpret P&L, fills, win rate, drawdown, or arm differences. Indicative data cannot establish a trading edge.'}


def html_report(report):
    text=escape(json.dumps(report,indent=2))
    heading=escape(report['experiment'])
    rows=''
    def money(c): return 'unknown' if c is None else f'${c/100:,.2f}'
    for name,s in report['arms'].items():
        rows+=('<tr>'+''.join(f'<td>{escape(str(x))}</td>' for x in (name,money(s['cash_cents']),money(s['equity_cents']),
                money(s['realized_cents']),money(s['unrealized_cents']),money(s['fees_cents']),money(s['max_drawdown_cents']),
                'OPEN' if s['position'] else 'none', 'PAUSED' if s['daily_pause'] or s['experiment_pause'] or s['unknown_mark'] else 'eligible'))+'</tr>')
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>{heading}</title>
<style>body{{font:16px system-ui;max-width:1250px;margin:35px auto;padding:20px;background:#101827;color:#eef3ff}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #40506b}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}p{{line-height:1.5}}</style>
<h1>{heading}</h1><h2>PLUMBING ONLY — NOT VALID FOR PROFIT, EXECUTION, OR AGENT-EFFICACY ANALYSIS</h2>
<p>{escape(report['evidence_kind'].upper())} evidence · $7,500 per alternative arm · mocked agents · no broker orders</p>
<p>{escape(report['real_data_readiness'])}. Real-money options: DISABLED.</p>
<table><thead><tr><th>Arm</th><th>Cash</th><th>Risk equity</th><th>Realized</th><th>Unrealized</th><th>Fees</th><th>Max drawdown</th><th>Position</th><th>Entries</th></tr></thead><tbody>{rows}</tbody></table>
<p>{escape(report['unknown_marks_note'])} {escape(report['costs_note'])}</p>
<details><summary>Inputs, proposals, positions and rejection reasons</summary><pre>{text}</pre></details>
<p>{escape(report['interpretation'])}</p></html>'''
