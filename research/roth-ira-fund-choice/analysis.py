"""Roth IRA fund choice: VT vs VTI+VXUS (70/30, 80/20) vs VOO (+ growth tilts), in household context.

Reuses the 401(k) analyzer's engine (run_portfolio, bootstrap_indices, CMA method) from
../401k-fund-choice/analysis.py. Reads cached Alpha Vantage files in data/raw/ and data/profiles/
(run ../401k-fund-choice/fetch.py-style download and fetch_profiles.py first). Deterministic.
Usage: python analysis.py   -> results/results.json, results/tables.md, charts/
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
import importlib.util  # noqa: E402

# The 401(k) engine is also named analysis.py, so load it under its own module name.
_spec = importlib.util.spec_from_file_location("k401_analysis", HERE.parent / "401k-fund-choice" / "analysis.py")
k401 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(k401)

RAW = HERE / "data" / "raw"
PROF = HERE / "data" / "profiles"
RESULTS = HERE / "results"
CHARTS = HERE / "charts"
SEED = 20261007
N_PATHS = 10_000
LAST_MONTH = pd.Period("2026-09", "M")  # last complete month in the data

# ---- the Roth saver (owner-reported, Oct 7 2026) ---------------------------------------------
ROTH_START = 5_967.0
ROTH_ANNUAL = 250 * 26 * 1.03  # $250 biweekly + 3% Robinhood Gold match = $6,695/yr
ROTH_MONTHLY = ROTH_ANNUAL / 12
AGE0, HORIZON_MONTHS = 22, 33 * 12

# ---- fund chains: (ticker, that class's ER %) newest first; returns shifted to the target ER ----
# Target ERs are Alpha Vantage ETF_PROFILE net expense ratios (profiles dated 2026-10-02).
SERIES = {
    "VTI": ([("VTI", .03), ("VTSAX", .04), ("VTSMX", .14)], 0.03),
    "VXUS": ([("VXUS", .05), ("VTSNX", .06), ("VGTSX", .17)], 0.05),
    "VOO": ([("VOO", .03), ("VFIAX", .04), ("VFINX", .14)], 0.03),
    "VT": ([("VT", .06)], 0.06),  # actual only (first full month Aug 2008)
    "QQQM": ([("QQQM", .15), ("QQQ", .20)], 0.15),
    "VUG": ([("VUG", .03), ("VIGRX", .17)], 0.03),
}
PORTFOLIOS = {
    "VT": {"VT": 1.0},
    "70/30": {"VTI": .70, "VXUS": .30},
    "80/20": {"VTI": .80, "VXUS": .20},
    "VOO": {"VOO": 1.0},
    "VTI": {"VTI": 1.0},
    "VT+20% QQQM": {"VT": .80, "QQQM": .20},
    "QQQM": {"QQQM": 1.0},
}
NAMES = {"VT": "VT (one fund)", "70/30": "VTI 70 / VXUS 30", "80/20": "VTI 80 / VXUS 20",
         "VOO": "VOO (S&P 500)", "VTI": "VTI only (intl held in taxable)",
         "VT+20% QQQM": "Tilt: VT 80 + QQQM 20", "QQQM": "Tilt: QQQM 100"}
# Forward real returns, same values as the 401(k) study (US large 4.2, mid 4.5, small 4.8, intl 5.0).
# Total market ~ 85% large / 10% mid / 5% small -> 4.3%. Growth funds get zero skill (= US large).
CMA_REAL = {"VTI": .043, "VOO": .042, "VXUS": .050, "QQQM": .042, "VUG": .042}

# ---- household (owner-reported Oct 7; 401(k) balance estimated from the Sep 29 study) ---------
TAXABLE = 150_000.0
EMERGENCY_CASH = 25_000.0
K401 = 18_000.0  # $16,825 on Sep 29 + about one paycheck; owner to confirm
LITE_SHARE_OF_TOTAL = 0.27
MU_SHARES = 50.97  # still in the project's records (output/REAL_POSITION_MU_20261002.md); owner to confirm
K401_W = {"SP500": .45, "INTL": .35, "MID": .10, "SMALL": .10}
# Information-technology sector weight per holding. ETF values from Alpha Vantage ETF_PROFILE; the
# API's VXUS/VT sector lists are truncated to US listings, so VXUS uses an approximate ~13% (FTSE
# All-World ex-US) and VT is derived from its US/intl mix. Mid/small 401(k) funds: approximate.
IT_W = {"VTI": .350, "VOO": .377, "QQQM": .577, "VUG": .572, "VXUS": .13, "SP500": .377, "INTL": .13,
        "MID": .13, "SMALL": .13, "LITE": 1.0, "MU": 1.0}
MU_IN = {"VTI": .0146, "VOO": .0163, "QQQM": .0512, "VUG": 0.0, "SP500": .0163}
LITE_IN = {"VTI": .0010, "VOO": .0011, "QQQM": .0035, "VUG": .0021, "SP500": .0011}


def quote(sym):
    return float(json.loads((PROF / f"GLOBAL_QUOTE_{sym}.json").read_text())["Global Quote"]["05. price"])


def profile(sym):
    return json.loads((PROF / f"ETF_PROFILE_{sym}.json").read_text())


def load_returns():
    prices = {}
    for path in sorted(RAW.glob("*.json")):
        if path.stem == "CPI":
            continue
        ts = json.loads(path.read_text())["Monthly Adjusted Time Series"]
        prices[path.stem] = pd.Series({pd.Period(d[:7], "M"): float(v["5. adjusted close"])
                                       for d, v in ts.items()}).sort_index()
    px = pd.DataFrame(prices).loc[:LAST_MONTH]
    return px.pct_change(fill_method=None).iloc[1:]


def build_series(rets):
    out, src = {}, {}
    for name, (chain, target) in SERIES.items():
        s = pd.Series(np.nan, index=rets.index)
        tag = pd.Series("", index=rets.index)
        for ticker, er in reversed(chain):
            r = rets[ticker] + (er - target) / 100 / 12
            ok = r.notna()
            s[ok], tag[ok] = r[ok], ticker
        out[name], src[name] = s, tag
    return pd.DataFrame(out), pd.DataFrame(src)


def vt_mix(series):
    """VT's current US/intl split, estimated by regressing VT on VTI and VXUS (last 36 months)."""
    w = series.loc["2023-10":, ["VT", "VTI", "VXUS"]].dropna()
    coef, *_ = np.linalg.lstsq(w[["VTI", "VXUS"]].to_numpy(), w["VT"].to_numpy(), rcond=None)
    us = coef[0] / coef.sum()
    fit = w[["VTI", "VXUS"]].to_numpy() @ np.array([us, 1 - us])
    te = (w["VT"] - fit).std() * np.sqrt(12)
    return float(us), float(te)


def stats(twr, bal, contributed):
    r = twr.pct_change().fillna(twr.iloc[0] - 1)
    roll12 = (1 + r).rolling(12).apply(np.prod, raw=True) - 1
    return {"CAGR": twr.iloc[-1] ** (12 / len(r)) - 1, "Volatility": r.std() * np.sqrt(12),
            "Max drawdown": (twr / twr.cummax()).min() - 1, "Worst 12m": roll12.min(),
            "Ending balance": bal.iloc[-1], "Contributed": contributed}


def backtest(series, start, label, use_proxy=False):
    frame = series.loc[start:].copy()
    ports = dict(PORTFOLIOS)
    if use_proxy:  # VT doesn't exist before mid-2008: stand-in at today's mix, labelled as such
        ports = {k: {("VT_PROXY" if a == "VT" else a): v for a, v in w.items()} for k, w in ports.items()}
    need = sorted({a for w in ports.values() for a in w})
    frame = frame.dropna(subset=need)
    out, curves = {}, {}
    for key, w in ports.items():
        twr = k401.run_portfolio(frame, w, 1.0, 0.0)
        bal = k401.run_portfolio(frame, w, ROTH_START, ROTH_MONTHLY)
        out[key] = stats(twr, bal, ROTH_START + len(frame) * ROTH_MONTHLY)
        curves[key] = twr
    out["_window"] = f"{frame.index[0]} to {frame.index[-1]} ({len(frame)} months) [{label}]"
    return out, pd.DataFrame(curves)


def monte_carlo(real, assets, vt_us):
    """Paired bootstrap (12-month blocks) and CMA-shifted runs; same draws for every portfolio."""
    rng = np.random.default_rng(SEED)
    idx = k401.bootstrap_indices(rng, len(real), N_PATHS, HORIZON_MONTHS)
    cma = real.copy()
    for a, g in CMA_REAL.items():
        x = real[a]
        cma[a] = x - x.mean() + (1 + g) ** (1 / 12) - 1 + x.var() / 2 - SERIES[a][1] / 100 / 12
    out = {}
    for model, hist in (("bootstrap", real), ("cma", cma)):
        h = hist.copy()
        # VT in the simulation = today's estimated mix of VTI/VXUS, charged VT's own higher ER
        blend_er = vt_us * SERIES["VTI"][1] + (1 - vt_us) * SERIES["VXUS"][1]
        h["VT"] = vt_us * h["VTI"] + (1 - vt_us) * h["VXUS"] - (SERIES["VT"][1] - blend_er) / 100 / 12
        R = h[assets + ["VT"]].to_numpy()[idx]  # paths x months x assets
        cols = assets + ["VT"]
        bals = {}
        for key, w in PORTFOLIOS.items():
            wv = np.array([w.get(c, 0.0) for c in cols])
            port = np.einsum("pma,a->pm", R, wv)
            assert np.isfinite(port).all(), key
            bal = np.empty((N_PATHS, HORIZON_MONTHS + 1))
            bal[:, 0] = ROTH_START
            for m in range(HORIZON_MONTHS):
                bal[:, m + 1] = bal[:, m] * (1 + port[:, m]) + ROTH_MONTHLY
            bals[key] = bal
        res = {}
        for key, bal in bals.items():
            end = bal[:, -1]
            dd = (bal / np.maximum.accumulate(bal, axis=1)).min(axis=1) - 1
            res[key] = {"P10 @55": np.percentile(end, 10), "Median @55": np.median(end),
                        "P90 @55": np.percentile(end, 90), "Median worst drop": np.median(dd),
                        "P(worse than VT at 55)": float((end < bals["VT"][:, -1]).mean())}
        out[model] = res
    return out


def household(vt_us, roth_key, mu_held):
    """Look-through dollars by bucket for the whole household under one Roth choice."""
    lite_px, mu_px = quote("LITE"), quote("MU")
    total = TAXABLE + ROTH_START + K401
    lite = LITE_SHARE_OF_TOTAL * total
    mu = MU_SHARES * mu_px if mu_held else 0.0
    index_taxable = TAXABLE - EMERGENCY_CASH - lite - mu
    hold = {"LITE": lite, "MU": mu, "VTI": .70 * index_taxable, "VXUS": .30 * index_taxable}
    for k, v in K401_W.items():
        hold["401k_" + k] = v * K401
    roth = {"VT": {"VTI": vt_us, "VXUS": 1 - vt_us}}.get(roth_key, None)
    for k, v in (roth or PORTFOLIOS[roth_key]).items():
        if k == "VT":  # VT inside a tilt portfolio
            hold["Roth_VTI"] = hold.get("Roth_VTI", 0) + v * vt_us * ROTH_START
            hold["Roth_VXUS"] = hold.get("Roth_VXUS", 0) + v * (1 - vt_us) * ROTH_START
        else:
            hold["Roth_" + k] = hold.get("Roth_" + k, 0) + v * ROTH_START
    base = lambda name: name.split("_", 1)[-1]  # noqa: E731
    equity = sum(hold.values())
    intl = sum(v for k, v in hold.items() if base(k) in ("VXUS", "INTL"))
    it = sum(v * IT_W[base(k)] for k, v in hold.items())
    mu_lt = mu + sum(v * MU_IN.get(base(k), 0) for k, v in hold.items() if base(k) not in ("MU", "LITE"))
    lite_lt = lite + sum(v * LITE_IN.get(base(k), 0) for k, v in hold.items() if base(k) not in ("MU", "LITE"))
    return {"total_assets": total, "equity": equity, "LITE $": lite, "LITE shares": lite / lite_px,
            "MU $": mu, "taxable index $": index_taxable, "intl % of stocks": intl / equity,
            "info-tech % of stocks": it / equity, "LITE % of stocks (look-through)": lite_lt / equity,
            "MU % of stocks (look-through)": mu_lt / equity,
            "LITE+MU % of total assets": (lite_lt + mu_lt) / total}


def correlations(rets):
    out = {}
    for start in ("2016-01", "2020-01"):
        w = rets.loc[start:, ["LITE", "MU", "VTI", "VXUS", "VT", "QQQ", "VUG"]].dropna()
        out[f"since {start}"] = w.corr().loc[["LITE", "MU"], ["VTI", "VXUS", "VT", "QQQ", "VUG"]].round(2).to_dict("index")
    return out


def fmt_pct(x):
    return f"{x*100:.1f}%"


def money(x):
    return f"${x:,.0f}"


def plot_curves(curves, title, path):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    colors = {"VT mix DIY": "#9bbbe6", "VT": "#2a78d6", "70/30": "#eb6834", "80/20": "#eda100", "VOO": "#1baf7a",
              "VTI": "#4a3aa7", "VT+20% QQQM": "#e87ba4", "QQQM": "#52514e"}
    for k in curves:
        ax.plot(curves.index.to_timestamp(), curves[k], label=NAMES[k], color=colors[k],
                lw=2.2 if k in ("VT", "70/30") else 1.4)
    ax.set_yscale("log")
    k401.style(ax, title, "Growth of $1 (log)")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main():
    RESULTS.mkdir(exist_ok=True)
    CHARTS.mkdir(exist_ok=True)
    rets = load_returns()
    series, src = build_series(rets)
    vt_us, vt_te = vt_mix(series)
    # Same US/intl mix as VT, built from the two cheaper funds: isolates VT's fee from its mix
    PORTFOLIOS["VT mix DIY"] = {"VTI": round(vt_us, 3), "VXUS": round(1 - vt_us, 3)}
    NAMES["VT mix DIY"] = f"VTI {vt_us*100:.0f} / VXUS {100-vt_us*100:.0f} (VT's mix, DIY)"
    series["VT_PROXY"] = vt_us * series["VTI"] + (1 - vt_us) * series["VXUS"] - (
        SERIES["VT"][1] - (vt_us * .03 + (1 - vt_us) * .05)) / 100 / 12

    bts = {}
    bts["post_covid"], c1 = backtest(series, "2020-01", "MAIN: post-COVID, actual funds (QQQM before Nov 2020 = QQQ)")
    bts["since_vt_2008"], c2 = backtest(series, "2008-08", "stress: since VT launch, incl. 2008 crash; older classes before each ETF existed")
    bts["long_2000"], c3 = backtest(series, "2000-01", "deep stress: 2000-2026; VT row = today's mix proxy", use_proxy=True)
    plot_curves(c1, "Roth options, post-COVID (Jan 2020 - Sep 2026)", CHARTS / "post_covid.png")
    plot_curves(c2, "Roth options since VT launch (Aug 2008 - Sep 2026)", CHARTS / "since_2008.png")

    cpi_rows = json.loads((RAW / "CPI.json").read_text())["data"]
    cpi = pd.Series({pd.Period(r["date"][:7], "M"): float(r["value"]) for r in cpi_rows
                     if r["value"] != "."}).sort_index().pct_change()
    assets = ["VTI", "VXUS", "VOO", "QQQM", "VUG"]
    hist = series.loc["2000-01":, assets].join(cpi.rename("CPI"), how="inner").dropna()
    real = hist[assets].apply(lambda c: (1 + c) / (1 + hist["CPI"]) - 1)
    mc = monte_carlo(real, assets, vt_us)

    hh = {}
    for mu_held in (False, True):
        for key in ("VT", "70/30", "80/20", "VOO", "VTI", "VT+20% QQQM", "QQQM"):
            hh[f"{'MU held' if mu_held else 'no MU'} | {key}"] = household(vt_us, key, mu_held)

    ers = {s: float(profile(s)["net_expense_ratio"]) for s in ["VT", "VTI", "VXUS", "VOO", "QQQM", "VUG", "SCHG"]}
    yields = {s: float(profile(s)["dividend_yield"]) for s in ["VT", "VTI", "VXUS", "VOO", "QQQM", "VUG"]}
    blended_er = {k: sum(v * ers[a] for a, v in w.items()) for k, w in PORTFOLIOS.items()}

    results = {"vt_us_weight_est": vt_us, "vt_proxy_tracking_error": vt_te, "expense_ratios": ers,
               "dividend_yields": yields, "blended_er": blended_er, "backtests": bts, "monte_carlo": mc,
               "household": hh, "correlations": correlations(rets),
               "quotes": {s: quote(s) for s in ["LITE", "MU", "VT", "VTI", "VXUS", "VOO"]},
               "sources": {k: src[k][src[k] != ""].value_counts().to_dict() for k in SERIES}}
    (RESULTS / "results.json").write_text(json.dumps(results, indent=1, default=float))

    lines = [f"VT estimated mix (regression on VTI/VXUS, Oct 2023-Sep 2026): **{vt_us*100:.1f}% US / "
             f"{(1-vt_us)*100:.1f}% intl**, tracking error {vt_te*100:.2f}%/yr\n",
             "| Option | Blended ER | $ per year on $10k |", "|---|---|---|"]
    lines += [f"| {NAMES[k]} | {v*100:.3f}% | ${v*1e4:.2f} |" for k, v in blended_er.items()]
    for name, bt in bts.items():
        lines += [f"\n### Backtest: {bt['_window']}\n",
                  "| Option | CAGR | Volatility | Max drawdown | Worst 12m | Ending balance (Roth $ in) |",
                  "|---|---|---|---|---|---|"]
        lines += [f"| {NAMES[k]} | {fmt_pct(s['CAGR'])} | {fmt_pct(s['Volatility'])} | {fmt_pct(s['Max drawdown'])} | "
                  f"{fmt_pct(s['Worst 12m'])} | {money(s['Ending balance'])} (of {money(s['Contributed'])}) |"
                  for k, s in bt.items() if not k.startswith("_")]
    for model, res in mc.items():
        lines += [f"\n### Monte Carlo to 55, {model} (today's dollars; $5,967 + $6,695/yr)\n",
                  "| Option | P10 | Median | P90 | Median worst drop | Paths ending below VT |", "|---|---|---|---|---|---|"]
        lines += [f"| {NAMES[k]} | {money(r['P10 @55'])} | {money(r['Median @55'])} | {money(r['P90 @55'])} | "
                  f"{fmt_pct(r['Median worst drop'])} | {fmt_pct(r['P(worse than VT at 55)'])} |" for k, r in res.items()]
    lines += ["\n### Household look-through by Roth choice\n",
              "| Scenario | Intl % of stocks | Info-tech % of stocks | LITE % (look-through) | MU % (look-through) | LITE+MU % of all assets |",
              "|---|---|---|---|---|---|"]
    lines += [f"| {k} | {fmt_pct(v['intl % of stocks'])} | {fmt_pct(v['info-tech % of stocks'])} | "
              f"{fmt_pct(v['LITE % of stocks (look-through)'])} | {fmt_pct(v['MU % of stocks (look-through)'])} | "
              f"{fmt_pct(v['LITE+MU % of total assets'])} |" for k, v in hh.items()]
    first = next(iter(hh.values()))
    lines += [f"\nTotal assets {money(first['total_assets'])}; LITE {money(first['LITE $'])} "
              f"(~{first['LITE shares']:.1f} sh @ ${quote('LITE'):,.2f}); taxable index money: "
              f"{money(hh['no MU | VT']['taxable index $'])} without MU, {money(hh['MU held | VT']['taxable index $'])} "
              f"if MU ({MU_SHARES} sh @ ${quote('MU'):,.2f} = {money(hh['MU held | VT']['MU $'])}) is still held."]
    lines += ["\n### Correlation of monthly returns\n", "```", json.dumps(results["correlations"], indent=1), "```"]
    (RESULTS / "tables.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
