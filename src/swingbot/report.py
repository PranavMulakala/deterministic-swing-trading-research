from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _equity_svg(rows: list[dict[str, str]], width: int = 900, height: int = 260) -> str:
    values = [float(row["equity"]) for row in rows]
    if not values:
        return ""
    low, high = min(values), max(values)
    span = high - low or 1.0
    points = []
    for i, value in enumerate(values):
        x = 20 + i * (width - 40) / max(1, len(values) - 1)
        y = 20 + (high - value) * (height - 40) / span
        points.append(f"{x:.2f},{y:.2f}")
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Strategy equity curve">'
        f'<polyline fill="none" stroke="#56d364" stroke-width="2" points="{" ".join(points)}"/>'
        f'<text x="20" y="16" fill="#9da7b3" font-size="12">High ${high:.2f}</text>'
        f'<text x="20" y="{height-4}" fill="#9da7b3" font-size="12">Low ${low:.2f}</text></svg>'
    )


def write_dashboard(output_dir: Path) -> Path:
    is_metrics = _read_json(output_dir / "metrics_in_sample.json")
    oos_metrics = _read_json(output_dir / "metrics_out_of_sample.json")
    oos_benchmarks = _read_json(output_dir / "benchmarks_out_of_sample.json")
    with (output_dir / "equity_out_of_sample.csv").open(newline="", encoding="utf-8") as handle:
        equity = list(csv.DictReader(handle))
    with (output_dir / "trades_out_of_sample.csv").open(newline="", encoding="utf-8") as handle:
        trades = list(csv.DictReader(handle))
    events = [
        json.loads(line) for line in (output_dir / "events_out_of_sample.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rejection_counts: dict[str, int] = {}
    for event in events:
        if event["event_type"] in ("entry_rejected", "order_rejected"):
            reason = str(event.get("reason", "unspecified"))
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    metric_rows = [
        ("Strategy IS", is_metrics),
        ("Strategy OOS", oos_metrics),
        *[(str(item["benchmark"]), item) for item in oos_benchmarks],
    ]
    table = "".join(
        "<tr>"
        f"<td>{html.escape(name)}</td>"
        f"<td>${float(row['final_equity']):.2f}</td>"
        f"<td>{float(row['total_return_pct']):.2f}%</td>"
        f"<td>{float(row['cagr_pct']):.2f}%</td>"
        f"<td>{float(row['max_drawdown_pct']):.2f}%</td>"
        f"<td>{html.escape(str(row.get('trade_count', row.get('rebalance_count', 'n/a'))))}</td>"
        "</tr>"
        for name, row in metric_rows
    )
    trade_rows = "".join(
        "<tr>" + "".join(
            f"<td>{html.escape(str(row.get(field, '')))}</td>"
            for field in (
                "symbol", "entry_date", "exit_date", "pnl", "planned_risk_pct",
                "exit_reason", "qualification", "invalidation",
            )
        ) + "</tr>"
        for row in trades[-20:]
    ) or '<tr><td colspan="8">No OOS trades</td></tr>'
    rejection_rows = "".join(
        f"<tr><td>{html.escape(reason)}</td><td>{count}</td></tr>"
        for reason, count in sorted(rejection_counts.items(), key=lambda item: (-item[1], item[0]))
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Swing Research v1</title><style>
body{{margin:0;background:#0d1117;color:#e6edf3;font:15px system-ui,sans-serif}}main{{max-width:1000px;margin:auto;padding:32px}}
h1,h2{{letter-spacing:-.02em}}.notice{{border-left:4px solid #f2cc60;background:#161b22;padding:14px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}}
table{{width:100%;border-collapse:collapse;background:#161b22}}th,td{{padding:10px;border-bottom:1px solid #30363d;text-align:right}}th:first-child,td:first-child{{text-align:left}}
svg{{width:100%;background:#161b22;border:1px solid #30363d;border-radius:8px}}code{{color:#79c0ff}}small{{color:#9da7b3}}
</style></head><body><main><h1>Deterministic ETF swing research — v1</h1>
<p class="notice"><strong>Paper-only research.</strong> Execution is disabled. These are historical simulations, not forecasts or trade recommendations.</p>
<div class="cards"><div class="card"><small>OOS final equity</small><h2>${float(oos_metrics['final_equity']):.2f}</h2></div>
<div class="card"><small>OOS return</small><h2>{float(oos_metrics['total_return_pct']):.2f}%</h2></div>
<div class="card"><small>OOS max drawdown</small><h2>{float(oos_metrics['max_drawdown_pct']):.2f}%</h2></div>
<div class="card"><small>OOS trades</small><h2>{int(oos_metrics['trade_count'])}</h2></div></div>
<h2>OOS equity curve</h2>{_equity_svg(equity)}
<h2>Measured comparison</h2><table><thead><tr><th>System</th><th>Final</th><th>Total return</th><th>CAGR</th><th>Max drawdown</th><th>Trades/rebalances</th></tr></thead><tbody>{table}</tbody></table>
<h2>Last 20 OOS trades</h2><table><thead><tr><th>Symbol</th><th>Entry</th><th>Exit</th><th>P&amp;L</th><th>Risk %</th><th>Exit reason</th><th>Why qualified</th><th>Invalidation</th></tr></thead><tbody>{trade_rows}</tbody></table>
<h2>OOS rejection reasons</h2><table><thead><tr><th>Reason</th><th>Count</th></tr></thead><tbody>{rejection_rows}</tbody></table>
<h2>Full audit files</h2><p><a href="trades_out_of_sample.csv">All OOS trades</a> · <a href="events_out_of_sample.jsonl">Every OOS event/rejection</a> · <a href="equity_out_of_sample.csv">Equity</a> · <a href="exposure_out_of_sample.csv">Exposure</a> · <a href="validation_report.json">Invariant validation</a> · <a href="milestone1_report.md">Research report</a></p>
<p><small>Run artifacts contain every signal, rejection, simulated fill, position change, P&amp;L mark, exposure, fee and modeled execution cost. See <code>../../methodology.md</code> for limits.</small></p>
</main></body></html>"""
    destination = output_dir / "dashboard.html"
    destination.write_text(document, encoding="utf-8")
    return destination


def write_milestone_report(output_dir: Path) -> Path:
    is_metrics = _read_json(output_dir / "metrics_in_sample.json")
    oos = _read_json(output_dir / "metrics_out_of_sample.json")
    benchmarks = {row["benchmark"]: row for row in _read_json(output_dir / "benchmarks_out_of_sample.json")}
    spy = benchmarks["spy_buy_and_hold"]
    momentum = benchmarks["monthly_top3_126d_momentum"]
    relative_spy = float(oos["total_return_pct"]) - float(spy["total_return_pct"])
    relative_momentum = float(oos["total_return_pct"]) - float(momentum["total_return_pct"])
    verdict = (
        "V1 is a lower-exposure, lower-drawdown research result, but it does not establish a superior return edge. "
        "It should not advance to broker paper execution unchanged."
    )
    content = f"""# Milestone 1 research report

## Verdict

{verdict}

## Measured results

| System | Period | Final equity | Total return | CAGR | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Pullback v1 IS | {is_metrics['start_date']} to {is_metrics['end_date']} | ${float(is_metrics['final_equity']):.2f} | {float(is_metrics['total_return_pct']):.2f}% | {float(is_metrics['cagr_pct']):.2f}% | {float(is_metrics['max_drawdown_pct']):.2f}% |
| Pullback v1 OOS | {oos['start_date']} to {oos['end_date']} | ${float(oos['final_equity']):.2f} | {float(oos['total_return_pct']):.2f}% | {float(oos['cagr_pct']):.2f}% | {float(oos['max_drawdown_pct']):.2f}% |
| SPY buy/hold OOS | {spy['start_date']} to {spy['end_date']} | ${float(spy['final_equity']):.2f} | {float(spy['total_return_pct']):.2f}% | {float(spy['cagr_pct']):.2f}% | {float(spy['max_drawdown_pct']):.2f}% |
| Momentum OOS | {momentum['start_date']} to {momentum['end_date']} | ${float(momentum['final_equity']):.2f} | {float(momentum['total_return_pct']):.2f}% | {float(momentum['cagr_pct']):.2f}% | {float(momentum['max_drawdown_pct']):.2f}% |

OOS v1 completed {oos['trade_count']} trades, won {float(oos['win_rate_pct']):.2f}%, averaged ${float(oos['average_trade_pnl']):.4f} per trade, had profit factor {float(oos['profit_factor']):.3f}, and incurred ${float(oos['total_modeled_execution_cost']):.2f} of modeled spread, slippage, and fees. Average market exposure was {float(oos['average_exposure_pct']):.2f}%. Its total return trailed SPY by {abs(relative_spy):.2f} percentage points and momentum by {abs(relative_momentum):.2f} points, while its drawdown was lower.

## Why it might work

Broad ETFs often retain medium/long-term trend persistence while short, sharp selloffs mean-revert. The 200-day filter attempts to isolate that setting; RSI(2) locates unusually weak closes; the recovery exit avoids demanding a large forecast. This is a plausible mechanism, not proof.

## What must be true

The signal must contain enough short-horizon rebound information to overcome frequent turnover costs. Daily adjusted bars must approximate executable opens/stops adequately. Cross-ETF signals must add diversification rather than duplicate the same market bet. Most importantly, the lower exposure and risk cap must provide enough drawdown benefit to justify giving up passive-market return.

## What would invalidate it

The implementation is invalid if next-bar timing, checksum reproducibility, fill reconciliation, or risk tests fail. The economic case is invalidated if the frozen OOS run remains materially weaker than both benchmarks after costs without a separately valued low-drawdown objective. On this run, that economic warning has fired: v1 underperformed both benchmarks. A future v2 must be newly preregistered and tested on a new untouched period; tuning v1 against this OOS set would contaminate it.

## Decision

Keep v1 as a reproducible baseline and evidence artifact. Do not connect it to a broker. Before any separate paper-execution milestone, independently validate event ordering and accounting, then design a genuinely new v2 hypothesis—without optimizing against the disclosed OOS results. See `methodology.md` for data and simulation limitations and `validation_report.json` for invariant checks.
"""
    destination = output_dir / "milestone1_report.md"
    destination.write_text(content, encoding="utf-8")
    return destination
