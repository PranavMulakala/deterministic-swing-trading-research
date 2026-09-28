"""Run the fixed historical pilot after importer and prepared-replay checks."""
import csv
import hashlib
import json
from pathlib import Path
import sys

from acquire_databento import ROOT, save, sha256
from import_databento import OUT, TRADE, QUOTE, TradeEvents, np
from engine import signals, validate_config
from replay_prepared import replay

REPORT = ROOT/'research/mnq_feasibility_v1/runs/pilot-01'
HERE=Path(__file__).parent


class Quotes:
    def __init__(self,rows):self.rows=rows
    def __len__(self):return len(self.rows)
    def __getitem__(self,i):
        row=self.rows[i]
        return dict(type='quote',**{k:int(row[k]) for k in ['ts_ns','seq','bid_ticks','ask_ticks','bid_size','ask_size']})


def main():
    if REPORT.exists():raise ValueError('Refusing to overwrite a pilot report')
    pins=json.loads((HERE/'runs/pre-import-frozen-files.json').read_text())
    if any(sha256(HERE/name)!=value for name,value in pins.items()):raise ValueError('Frozen source changed')
    cfg=json.loads((HERE/'config.json').read_text());validate_config(cfg)
    manifest=json.loads((OUT/'manifest.json').read_text())
    if manifest['adapter_sha256']!=sha256(HERE/'import_databento.py'):raise ValueError('Importer changed since data preparation')
    if manifest['protocol_sha256']!=sha256(HERE/'IMPORT_PROTOCOL.md'):raise ValueError('Import protocol changed')
    sessions=[];previous=None
    for s in manifest['sessions']:
        for field in ['trades','quotes']:
            if sha256(OUT/s[field]) != s['trade_sha256' if field=='trades' else 'quote_sha256']:
                raise ValueError('Prepared data changed')
        t=np.memmap(OUT/s['trades'],dtype=TRADE,mode='r')
        q=np.memmap(OUT/s['quotes'],dtype=QUOTE,mode='r')
        trade_session=dict(s,events=TradeEvents(t))
        generated,note=signals(trade_session,previous,cfg)
        sessions.append(dict(date=s['date'],signals=generated,note=note,quotes=Quotes(q),times=q['ts_ns']))
        previous=trade_session
        print('Frozen signals',s['date'],len(generated),note,flush=True)
    scenarios=[]
    for cost in cfg['scenarios']:
        row=replay(sessions,cfg,cost);scenarios.append(row)
        print(cost['name'], 'patterns',row['pattern_signals'],'risk fits',row['risk_fit_signals'],
              'entries',row['entries'],'net',row['closed_trade_net_pnl'],flush=True)
    report=dict(status='HISTORICAL_PILOT_DIAGNOSTIC_NOT_TRADING_READINESS',evidence='HISTORICAL',
        initial_cash=cfg['initial_cash'],initial_risk_budget=cfg['initial_cash']*cfg['risk_fraction'],
        cost_status=cfg['cost_status'],scenarios=scenarios,
        source='Databento MNQU6 approved pilot, Aug 31 warmup and Sep 1-4 evaluation',
        equity_storage='Quotes while exposed and at decisions; redundant flat marks omitted without changing equity or pauses.',
        data_expense_usd='11.06613318994642',data_expense_in_trading_ledger=False,
        limitations=['Four evaluation sessions are insufficient to establish an edge.',
            'Fees and slippage are declared scenarios, not verified broker costs.',
            'Capture-time acquisition bounds do not independently establish every exchange event at session boundaries.',
            'Hypothetical exchange-time latency and top-of-book availability do not prove broker fills.',
            'Source minute coverage and flags do not independently certify venue completeness.',
            'No live-trading or paper-broker readiness established.'],
        provenance=dict(import_manifest_sha256=sha256(OUT/'manifest.json'),
            files={p.name:sha256(p) for p in sorted(HERE.iterdir()) if p.suffix in ('.py','.json','.md')},
            frozen_sources_unchanged=True))
    REPORT.mkdir()
    save(REPORT/'report.json',report)
    with (REPORT/'signals.csv').open('x',newline='') as stream:
        fields=['scenario','id','day','direction','signal_ns','entry_ns','entry_ticks','stop_ticks',
                'stop_distance_ticks','spread_ticks','planned_risk','risk_fits','planned_net_reward','net_reward_risk','reason','portfolio_reason']
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for result in scenarios:
            decisions={d['id']:d for d in result['decisions']}
            for s in result['screens']:
                writer.writerow(dict(s,scenario=result['scenario']['name'],portfolio_reason=decisions.get(s['id'],{}).get('portfolio_reason')))
    lines=['# First real-data MNQ pilot','',
        '**Observed-data diagnostic; costs and broker execution remain unverified.**','',
        'Five sessions were imported; August 31 is warmup and September 1–4 are evaluated. ',
        'The frozen setup, $5,000 simulated account, and $12.50 initial planned-risk budget were unchanged.','',
        '| Cost scenario | Patterns | Risk assessable | Risk fits | Fits / patterns | Entries | Closed net P&L | Observed drawdown |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in scenarios:
        pct='N/A' if r['risk_fit_pct_of_all_patterns'] is None else f"{r['risk_fit_pct_of_all_patterns']:.2f}%"
        lines.append(f"| {r['scenario']['name']} | {r['pattern_signals']} | {r['risk_assessable_signals']} | {r['risk_fit_signals']} | {pct} | {r['entries']} | ${r['closed_trade_net_pnl']:.2f} | ${r['max_observed_drawdown_dollars']:.2f} |")
    lines+=['','The fee2/fee4 labels mean $2/$4 total entry-and-exit fees; slip0/1/2 are extra adverse ticks per side.',
        'Risk-fit percentages describe the observed patterns, not a probability of future success.',
        'No patterns means the fit percentage is unknown; no entries means losses and pauses were not meaningfully exercised.',
        'Zero observed drawdown does not mean a risk-free strategy. Data expense of about $11.07 is separate from trading P&L.','',
        '## Evidence and limits','',
        'See `report.json` for every signal, decision, trade, pause, and retained equity mark; `signals.csv` is the compact decision table.',
        'Minute bars passed an independent calculation check. Prepared-array hashes and source hashes are included in the manifests.',
        'The replay was checked against the original engine on long/short and randomized multi-session fixtures before these outcomes were opened.',
        'Boundary completeness, calendar assumptions beyond these dates, account costs, margin, and actual broker execution remain limitations.',
        'This small pilot cannot approve live money. Do not loosen the setup or risk budget merely because the sample is sparse.','']
    (REPORT/'REPORT.md').write_text('\n'.join(lines))
    print('Saved:',REPORT,flush=True)


if __name__=='__main__':main()
