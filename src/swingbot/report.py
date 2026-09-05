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
            for field in ("symbol", "entry_date", "exit_date", "pnl", "exit_reason")
        ) + "</tr>"
        for row in trades[-20:]
    ) or '<tr><td colspan="5">No OOS trades</td></tr>'
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
<h2>Last 20 OOS trades</h2><table><thead><tr><th>Symbol</th><th>Entry</th><th>Exit</th><th>P&amp;L</th><th>Reason</th></tr></thead><tbody>{trade_rows}</tbody></table>
<p><small>Run artifacts contain every signal, rejection, simulated fill, position change, P&amp;L mark, exposure, fee and modeled execution cost. See <code>methodology.md</code> for limits.</small></p>
</main></body></html>"""
    destination = output_dir / "dashboard.html"
    destination.write_text(document, encoding="utf-8")
    return destination
