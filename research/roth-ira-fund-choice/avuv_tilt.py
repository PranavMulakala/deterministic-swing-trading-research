"""Roth test: VT 80 + AVUV 20 vs VT 100 (plan: AVUV_TILT_PLAN_20261008.md, written before this ran).

Reuses analysis.py (same data loader, VT mix estimate, Monte Carlo, contributions). AVUV before Oct 2019 =
DFSVX shifted to AVUV's ER. Usage: python avuv_tilt.py -> results/avuv_tilt.json, results/avuv_tilt.md
"""
import json

import numpy as np
import pandas as pd

import analysis as roth  # its module globals (SERIES, PORTFOLIOS, CMA_REAL) are patched below

k401 = roth.k401

AVUV_ER = 0.25
roth.SERIES["AVUV"] = ([("AVUV", AVUV_ER), ("DFSVX", .30)], AVUV_ER)
roth.PORTFOLIOS.clear()
roth.PORTFOLIOS.update({"VT": {"VT": 1.0}, "VT+20% AVUV": {"VT": .80, "AVUV": .20},
                        "VT+20% QQQM": {"VT": .80, "QQQM": .20}})
roth.NAMES.update({"VT+20% AVUV": "VT 80 + AVUV 20", "VT+20% QQQM": "VT 80 + QQQM 20 (Reddit-style tilt)"})
PREMIUMS = {"no premium (4.3%)": .043, "base (4.8%)": .048, "+1 pt (5.8%)": .058}


def money(x):
    return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"


def dollar_backtest(series, start, label, use_proxy=False):
    frame = series.loc[start:].copy()
    ports = {k: dict(w) for k, w in roth.PORTFOLIOS.items()}
    if use_proxy:
        ports = {k: {("VT_PROXY" if a == "VT" else a): v for a, v in w.items()} for k, w in ports.items()}
    need = sorted({a for w in ports.values() for a in w})
    frame = frame.dropna(subset=need)
    out = {}
    for key, w in ports.items():
        twr = k401.run_portfolio(frame, w, 1.0, 0.0)
        bal = k401.run_portfolio(frame, w, roth.ROTH_START, roth.ROTH_MONTHLY)
        pnl = bal.diff().fillna(bal.iloc[0] - roth.ROTH_START) - roth.ROTH_MONTHLY  # market gain/loss per month
        out[key] = {
            "Ending balance": bal.iloc[-1],
            "Contributed": roth.ROTH_START + len(frame) * roth.ROTH_MONTHLY,
            "CAGR": twr.iloc[-1] ** (12 / len(frame)) - 1,
            "Worst drop %": (twr / twr.cummax()).min() - 1,
            "Worst drop $": (bal - bal.cummax()).min(),
            "Worst month $": pnl.min(), "Worst month": str(pnl.idxmin()),
            "Worst 12m $": pnl.rolling(12).sum().min(),
            "% months up": float((pnl > 0).mean()),
        }
    out["_window"] = f"{frame.index[0]} to {frame.index[-1]} ({len(frame)} months) [{label}]"
    return out


def main():
    rets = roth.load_returns()
    series, src = roth.build_series(rets)
    vt_us, _ = roth.vt_mix(series)
    series["VT_PROXY"] = vt_us * series["VTI"] + (1 - vt_us) * series["VXUS"] - (
        roth.SERIES["VT"][1] - (vt_us * .03 + (1 - vt_us) * .05)) / 100 / 12

    # proxy check: AVUV vs DFSVX over their common months
    both = rets[["AVUV", "DFSVX"]].dropna()
    proxy = {"months": len(both), "first": str(both.index[0]), "correlation": float(both.corr().iloc[0, 1]),
             "AVUV CAGR": float((1 + both["AVUV"]).prod() ** (12 / len(both)) - 1),
             "DFSVX CAGR": float((1 + both["DFSVX"]).prod() ** (12 / len(both)) - 1),
             "tracking error": float((both["AVUV"] - both["DFSVX"]).std() * np.sqrt(12))}

    bts = {"post_covid": dollar_backtest(series, "2020-01", "MAIN: post-COVID; AVUV actual all window"),
           "since_2008": dollar_backtest(series, "2008-08", "stress (decides rule 3): DFSVX before Oct 2019"),
           "long_2000": dollar_backtest(series, "2000-01", "deep stress: VT = today's-mix proxy before 2008",
                                        use_proxy=True)}

    cpi_rows = json.loads((roth.RAW / "CPI.json").read_text())["data"]
    cpi = pd.Series({pd.Period(r["date"][:7], "M"): float(r["value"]) for r in cpi_rows
                     if r["value"] != "."}).sort_index().pct_change()
    assets = ["VTI", "VXUS", "VOO", "QQQM", "VUG", "AVUV"]
    hist = series.loc["2000-01":, assets].join(cpi.rename("CPI"), how="inner").dropna()
    real = hist[assets].apply(lambda c: (1 + c) / (1 + hist["CPI"]) - 1)
    mc = {}
    for label, g in PREMIUMS.items():
        roth.CMA_REAL["AVUV"] = g
        res = roth.monte_carlo(real, assets, vt_us)
        mc[label] = res["cma"]
        mc.setdefault("bootstrap (info)", res["bootstrap"])

    corr = {}
    for name, cols, start in (("AVUV actual", ["AVUV"], "2019-11"), ("small value (DFSVX)", ["DFSVX"], "2016-01")):
        w = rets.loc[start:, ["LITE", "MU", "VT", "QQQ"] + cols].dropna()
        corr[f"{name} since {start}"] = w.corr().loc[["LITE", "MU"], cols + ["VT", "QQQ"]].round(2).to_dict("index")

    vt, tilt = mc["base (4.8%)"]["VT"]["Median @55"], mc["base (4.8%)"]["VT+20% AVUV"]["Median @55"]
    vt0, tilt0 = mc["no premium (4.3%)"]["VT"]["Median @55"], mc["no premium (4.3%)"]["VT+20% AVUV"]["Median @55"]
    dd_vt, dd_tilt = bts["since_2008"]["VT"]["Worst drop $"], bts["since_2008"]["VT+20% AVUV"]["Worst drop $"]
    rules = {"1 forward median >= VT": (tilt >= vt, f"{money(tilt)} vs {money(vt)}"),
             "2 no-premium cost < 3%": (tilt0 / vt0 - 1 > -0.03, f"{(tilt0/vt0-1)*100:+.1f}%"),
             "3 since-2008 $ drop <= 1.10x VT": (dd_tilt >= 1.10 * dd_vt, f"{money(dd_tilt)} vs {money(dd_vt)} "
                                                 f"({dd_tilt/dd_vt:.2f}x)")}
    verdict = "ADOPT" if all(ok for ok, _ in rules.values()) else "DO NOT ADOPT"

    out = {"proxy_check": proxy, "backtests": bts, "monte_carlo": mc, "correlations": corr,
           "rules": {k: {"pass": bool(ok), "detail": d} for k, (ok, d) in rules.items()}, "verdict": verdict,
           "avuv_sources": src["AVUV"][src["AVUV"] != ""].value_counts().to_dict()}
    (roth.RESULTS / "avuv_tilt.json").write_text(json.dumps(out, indent=1, default=float))

    L = [f"# VT 80 + AVUV 20 vs VT 100: verdict **{verdict}**\n"]
    L += [f"- Rule {k}: **{'PASS' if ok else 'FAIL'}** ({d})" for k, (ok, d) in rules.items()]
    L += [f"\nProxy check ({proxy['first']}+, {proxy['months']} months): AVUV {proxy['AVUV CAGR']*100:.1f}%/yr vs "
          f"DFSVX {proxy['DFSVX CAGR']*100:.1f}%/yr, correlation {proxy['correlation']:.3f}, "
          f"tracking error {proxy['tracking error']*100:.1f}%/yr"]
    for bt in bts.values():
        L += [f"\n### {bt['_window']}\n", "| Option | Ending (of $ in) | CAGR | Worst drop | Worst drop $ | "
              "Worst month $ | Worst 12m $ | Months up |", "|---|---|---|---|---|---|---|---|"]
        L += [f"| {roth.NAMES[k]} | {money(s['Ending balance'])} (of {money(s['Contributed'])}) | "
              f"{s['CAGR']*100:.1f}% | {s['Worst drop %']*100:.1f}% | {money(s['Worst drop $'])} | "
              f"{money(s['Worst month $'])} ({s['Worst month']}) | {money(s['Worst 12m $'])} | "
              f"{s['% months up']*100:.0f}% |" for k, s in bt.items() if not k.startswith("_")]
    L += ["\n### Monte Carlo to 55 (today's dollars)\n", "| Model | Option | P10 | Median | P90 | Median worst drop |",
          "|---|---|---|---|---|---|"]
    for model, res in mc.items():
        L += [f"| {model} | {roth.NAMES[k]} | {money(r['P10 @55'])} | {money(r['Median @55'])} | "
              f"{money(r['P90 @55'])} | {r['Median worst drop']*100:.1f}% |" for k, r in res.items()]
    L += ["\n### Correlation with LITE and MU (monthly)\n", "```", json.dumps(corr, indent=1), "```"]
    (roth.RESULTS / "avuv_tilt.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
