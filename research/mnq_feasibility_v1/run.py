"""Immutable offline reports. No data argument means a missing-data report."""
import argparse
import csv
import hashlib
import json
from math import floor
from pathlib import Path

from .engine import analyze, validate_config
from .fixture import dataset

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def budget_table(cfg):
    budget = cfg['initial_cash'] * cfg['risk_fraction']
    # Distance is from the un-slipped executable entry side to the stop.
    return [{'scenario': s['name'], 'budget': budget,
             'round_trip_fee': s['round_trip_fee'], 'slippage_ticks_per_side': s['slippage_ticks_per_side'],
             'max_quote_to_stop_ticks': max(0, floor((budget - s['round_trip_fee']) / cfg['tick_value']
                                                   - 2 * s['slippage_ticks_per_side']))}
            for s in cfg['scenarios']]


def report_markdown(report):
    lines = ['# MNQ feasibility report', '', '**Status: ' + report['status'] + '**', '',
             f"Starting simulated cash: ${report['initial_cash']:,.2f}. Initial per-entry planned-loss budget: ${report['initial_risk_budget']:.2f}.", '',
             '## What we can calculate without market data', '',
             'These fee/slippage scenarios are assumptions, not a verified broker quote.', '',
             '| Scenario | Fee for entry + exit | Extra slippage each side | Maximum quote-to-stop distance |',
             '|---|---:|---:|---:|']
    for row in report['budget_table']:
        ticks = row['max_quote_to_stop_ticks']
        lines.append(f"| {row['scenario']} | ${row['round_trip_fee']:.2f} | {row['slippage_ticks_per_side']} ticks | {ticks} ticks / {ticks * .25:.2f} points |")
    lines += ['', 'The observed spread is already included by buying at the ask and selling at the bid.',
              'This is a maximum allowable distance, not a recommended stop placement.', '',
              '## Answers to the three questions', '']
    if not report.get('scenarios'):
        lines += ['1. Percentage of signals fitting the budget: **unknown; no MNQ tape supplied**.',
                  '2. Performance after realistic costs: **unknown; verified broker fees and MNQ quotes missing**.',
                  '3. Losses and drawdowns under pause rules: **unknown; no real replay performed**.']
    else:
        lines += ['**If this is SYNTHETIC, every figure below is a software demonstration, not trading evidence.**', '',
                  '| Scenario | Patterns | Risk known | Risk fits | Fits / all patterns | Entries | Closed net P&L | Ending equity | Observed max DD |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for r in report['scenarios']:
            pct = r['risk_fit_pct_of_all_patterns']
            ending = 'UNKNOWN' if r['ending_equity'] is None else f"${r['ending_equity']:.2f}"
            pct_text = 'N/A' if pct is None else f'{pct:.1f}%'
            lines.append(f"| {r['scenario']['name']} | {r['pattern_signals']} | {r['risk_assessable_signals']} | {r['risk_fit_signals']} | {pct_text} | {r['entries']} | ${r['closed_trade_net_pnl']:.2f} | {ending} | ${r['max_observed_drawdown_dollars']:.2f} |")
        lines += ['', 'Read report.json for every screen, rejection, trade, mark, and data-quality issue.',
                  'Unknown quotes remain in the total-pattern denominator. Known-risk fit rate is also reported.',
                  'Observed drawdown is only a lower bound when a position crosses a data gap.',
                  'Different scenarios may admit different trades. Their totals are not matched-trade cost comparisons.']
    lines += ['', '## Boundaries', '',
              'No broker connection or orders. No strategy profitability or live-trading approval.',
              'Data/platform subscriptions, taxes, and broker margin constraints are not included in the trading ledger.',
              'Subtract actual fixed expenses separately before assessing the economics of the project.',
              'A historical input label and coverage declaration do not prove the vendor export is complete.',
              'The protocol and source hashes are recorded in report.json. Do not replace a prior output directory.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--data', type=Path, help='Normalized JSON market tape; see DATA_CONTRACT.md')
    group.add_argument('--demo', action='store_true', help='Run invented data, NEVER market evidence')
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing directories refused')
    args = parser.parse_args()
    cfg = json.loads((ROOT / 'config.json').read_text())
    validate_config(cfg)
    data = dataset() if args.demo else json.loads(args.data.read_text()) if args.data else None
    report = analyze(data, cfg) if data is not None else {
        'status': 'BLOCKED_MISSING_MNQ_DATA_AND_VERIFIED_COSTS', 'evidence': 'NO_MARKET_DATA',
        'scenarios': [], 'real_signal_fit_percentage': None, 'real_net_pnl': None, 'real_drawdown': None}
    report['budget_table'] = budget_table(cfg)
    report['initial_cash'] = cfg['initial_cash']
    report['initial_risk_budget'] = cfg['initial_cash'] * cfg['risk_fraction']
    report['provenance'] = {'files': {p.name: digest(p) for p in sorted(ROOT.iterdir())
                                    if p.suffix in ('.py', '.json', '.md')},
                            'input_sha256': digest(args.data) if args.data else None,
                            'input_file': str(args.data.resolve()) if args.data else None}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (args.output / 'REPORT.md').write_text(report_markdown(report))
    with (args.output / 'budget.csv').open('w', newline='') as f:
        rows = report['budget_table']
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({'status': report['status'], 'report': str((args.output / 'REPORT.md').resolve())}))


if __name__ == '__main__':
    main()
