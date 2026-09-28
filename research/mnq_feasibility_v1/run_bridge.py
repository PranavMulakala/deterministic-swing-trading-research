"""Extra exploratory Aug 28->31 seam check using already purchased data only."""
from datetime import datetime, timezone
import json
from pathlib import Path

from acquire_databento import ROOT, save, sha256
from engine import bars, signals, validate_config
from import_databento import TRADE, QUOTE, TradeEvents, independent_bar_check, np
from replay_prepared import replay
from run_imported import Quotes
from screen_trade_extension import independent_signals


HERE = Path(__file__).resolve().parent
REPORT = HERE/'runs/bridge-01'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def main():
    require(not REPORT.exists(), 'Preserve existing exploratory report')
    pins = json.loads((HERE/'runs/pre-import-frozen-files.json').read_text())
    require(all(sha256(HERE/name)==value for name,value in pins.items()), 'Frozen source changed')
    cfg = json.loads((HERE/'config.json').read_text())
    validate_config(cfg)
    pilot = HERE/'data/import-v1'
    extension = HERE/'data/trade-extension-import-v1'
    pm = json.loads((pilot/'manifest.json').read_text())
    em = json.loads((extension/'manifest.json').read_text())
    old = next(s for s in em['sessions'] if s['date']=='2026-08-28')
    current = next(s for s in pm['sessions'] if s['date']=='2026-08-31')
    require(old['contract']==current['contract']=='MNQU6', 'Contract seam mismatch')
    checks=[]; sessions=[]; audited=[]
    for directory,row,trade_field in [(extension,old,'trade_file'),(pilot,current,'trades')]:
        trade_file=directory/row[trade_field]
        require(sha256(trade_file)==row['trade_sha256'], 'Prepared trades changed')
        require(sha256(ROOT/row['source_file'])==row['source_sha256'], 'Purchased source changed')
        trades=np.memmap(trade_file,dtype=TRADE,mode='r')
        require(len(trades)==row['trade_count'], 'Trade count changed')
        session=dict(date=row['date'],contract='MNQU6',events=TradeEvents(trades))
        calculated=bars(session)
        cached={int(k):v for k,v in json.loads((directory/(row['date']+'.bars.json')).read_text()).items()}
        require(cached==calculated, 'Previously audited bars differ from source-array reconstruction')
        audit=independent_bar_check(trades,row['date'],cached)
        checks.append(dict(date=row['date'],trade_file=str(trade_file.relative_to(ROOT)),
            trade_sha256=row['trade_sha256'],source_file=row['source_file'],source_sha256=row['source_sha256'],
            trade_count=len(trades),bar_audit=audit))
        sessions.append(session);audited.append(cached)
    generated,note=signals(sessions[1],sessions[0],cfg)
    separate,counts=independent_signals('2026-08-31',audited[1],audited[0],cfg)
    require(note is None and generated==separate, 'Independent frozen signal check failed')
    quote_path=pilot/current['quotes']
    require(sha256(quote_path)==current['quote_sha256'], 'Prepared quotes changed')
    quote_rows=np.memmap(quote_path,dtype=QUOTE,mode='r')
    require(len(quote_rows)==current['quote_count'], 'Quote count changed')
    scenarios=[]
    if generated:
        prepared=[dict(date='2026-08-31',signals=generated,note=note,
                       quotes=Quotes(quote_rows),times=quote_rows['ts_ns'])]
        for cost in cfg['scenarios']:
            scenarios.append(replay(prepared,cfg,cost))
    require(all(sha256(HERE/name)==value for name,value in pins.items()), 'Frozen source changed during check')
    result=dict(status='EXPLORATORY_SEAM_DIAGNOSTIC_NOT_TRADING_READINESS',
        created_at=datetime.now(timezone.utc).isoformat(),evidence='HISTORICAL',
        diagnostic_day='2026-08-31',previous_session_day='2026-08-28',contract='MNQU6',
        rationale='August 31 was original-pilot warmup; the newly available August 28 completes its same-contract prior-session reference.',
        separate_from_preserved_pilot_and_extension_reports=True,held_out=False,
        newly_purchased_data=False,new_data_expense_usd='0',complete_patterns=len(generated),
        signals=generated,independent_signal_check=dict(matched=True,**counts),
        scenarios=scenarios,replay_performed=bool(generated),
        risk_fit_percentage=None if not generated else 'SEE_SCENARIOS',
        cost_status=cfg['cost_status'],
        sources=checks,quote_file=str(quote_path.relative_to(ROOT)),
        quote_sha256=current['quote_sha256'],quote_count=len(quote_rows),
        provenance=dict(frozen_files=pins,bridge_script_sha256=sha256(Path(__file__)),
            pilot_manifest_sha256=sha256(pilot/'manifest.json'),
            extension_manifest_sha256=sha256(extension/'manifest.json'),
            independent_checker_sha256=sha256(HERE/'screen_trade_extension.py'),
            prepared_replay_sha256=sha256(HERE/'replay_prepared.py')),
        limitations=[
            'Extra exploratory check added after inspecting the earlier pilot and extension; not an untouched validation sample.',
            'Separate diagnostic with fresh $5000 simulated equity if replayed; it does not splice or claim a continuous portfolio ledger across prior reports.',
            'All cost scenarios remain illustrative, not verified broker fees or observed execution.',
            'Source/cached-bar agreement and 390-minute coverage do not independently certify exchange completeness.',
            'Capture-time boundaries may omit late-arriving exchange-time records.',
            'No broker paper execution, live order, strategy profitability, or live readiness is established.'])
    REPORT.mkdir()
    save(REPORT/'report.json',result)
    lines=['# Exploratory August 28 to August 31 seam check','',
        '**Extra diagnostic only; not held-out validation or trading readiness.**','',
        'August 28 supplies the prior-session high and low for August 31, which was originally warmup.',
        f'The unchanged engine and a separate signal calculation both found **{len(generated)} qualifying patterns** on August 31.','',
        'Both trade-array and raw-source hashes were verified, cached bars matched fresh reconstruction, and both full sessions passed independent OHLC/VWAP/variance checks. The existing August 31 quote-array hash was also verified.','',
        '**Additional data purchase: $0.** Existing pilot and extension reports are preserved.','']
    if scenarios:
        lines += ['| Cost scenario | Patterns | Risk assessable | Risk fits | Entries | Closed net P&L | Observed drawdown |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        for row in scenarios:
            lines.append(f"| {row['scenario']['name']} | {row['pattern_signals']} | {row['risk_assessable_signals']} | {row['risk_fit_signals']} | {row['entries']} | ${row['closed_trade_net_pnl']:.2f} | ${row['max_observed_drawdown_dollars']:.2f} |")
        lines += ['', 'The four illustrative scenarios use the already purchased August 31 quotes and a separate $5,000 simulated starting balance. These are hypothetical results with unverified costs.']
    else:
        lines += ['There were no patterns to replay. Risk fit, win rate, profitability and trade drawdown remain unmeasured for this diagnostic; they are not zero-risk results.']
    lines += ['', 'This date was previously inspected, and this extra check was chosen after earlier results. It cannot be described as untouched validation. No paper or live orders were placed.','']
    with (REPORT/'REPORT.md').open('x') as stream:
        stream.write('\n'.join(lines))
    print(json.dumps(dict(report=str(REPORT),patterns=len(generated),independent_check=counts,
                          replay_scenarios=len(scenarios),additional_data_expense_usd='0')))


if __name__=='__main__':
    main()
