"""Readable, escaped local report with unknown marks kept distinct from risk marks."""
from collections import Counter
from html import escape
import json
from datetime import datetime, timezone


def build(ledger):
    rows=ledger.history()
    arms={}
    for name,s in ledger.state().items():
        pos=s['position']
        reasons=Counter(r['decisions'][name]['verdict'] for r in rows)
        fill_reasons=Counter(a['reason'] for r in rows for a in r['decisions'][name]['actions'] if a['kind']=='unfilled')
        arms[name]={**s,'unrealized_cents':None if pos and s['unknown_mark'] else (pos['mark_cents']-pos['debit_cents'] if pos else 0),
                    'net_pnl_cents':s['equity_cents']-750000,'decision_reasons':dict(reasons),
                    'unfilled_reasons':dict(fill_reasons)}
    latest=rows[-1] if rows else None
    return {'experiment':ledger.cfg['experiment'],'capital_per_arm_cents':750000,'evidence_kind':ledger.kind,
            'local_software':'see HANDOFF.md for tested release verdict',
            'real_data_readiness':'BLOCKED: normalized options feed and coverage not verified' if ledger.kind=='fixture' or not latest or not latest['candidate'] else 'UNVERIFIED: sourced packet accepted; provider authenticity and sustained coverage need verification',
            'real_money':'NOT AUTHORIZED','model':'mock-v1; zero API calls',
            'costs_note':'Fees are debited. Spread/slippage figures are attribution, not additional debits. External data/cloud costs unverified.',
            'unknown_marks_note':'Unknown liquidation marks use worst-case loss plus reserved exit fee for risk decisions; these are not observed prices.',
            'generated_at':datetime.now(timezone.utc).isoformat(),'last_observation':latest['observed_at'] if latest else None,
            'observations':len(rows),'available_data':{k:bool(latest and k in latest['packet']) for k in ('chain','underlying','bars','calendar','events','news')},
            'contract_rejections':dict(Counter(x for r in rows for x in r['contract_rejections'])),
            'arms':arms,'last_decisions':latest['decisions'] if latest else {},
            'recent_decisions':[{'event_id':r['event_id'],'observed_at':r['observed_at'],'packet_hash':r['packet_hash'],
                                 'candidate':r['candidate'],'decisions':r['decisions']} for r in rows[-20:]],
            'sources':{k:{f:latest['packet'][k].get('provenance',{}).get(f) for f in ('source','feed','published_at','received_at')}
                       for k in ('chain','underlying','calendar','events','news') if latest and isinstance(latest['packet'].get(k),dict)},
            'interpretation':'Software and simulated outcomes do not establish a trading edge. Three arms are alternatives with matched inputs.'}


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
<h1>{heading}</h1><p>{escape(report['evidence_kind'].upper())} evidence · $7,500 per alternative arm · mocked agents · no broker orders</p>
<p>{escape(report['real_data_readiness'])}. Real-money options: NOT AUTHORIZED.</p>
<table><thead><tr><th>Arm</th><th>Cash</th><th>Risk equity</th><th>Realized</th><th>Unrealized</th><th>Fees</th><th>Max drawdown</th><th>Position</th><th>Entries</th></tr></thead><tbody>{rows}</tbody></table>
<p>{escape(report['unknown_marks_note'])} {escape(report['costs_note'])}</p>
<details><summary>Inputs, proposals, positions and rejection reasons</summary><pre>{text}</pre></details>
<p>{escape(report['interpretation'])}</p></html>'''
