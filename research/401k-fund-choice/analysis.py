"""401(k) fund choice: backtest + Monte Carlo + crash scenarios for options A, B, C and hybrids.

Reads the cached Alpha Vantage files in data/raw/ (run fetch.py first) and writes charts/, results/.
Deterministic: every random draw comes from one seeded generator.  Usage: python analysis.py
"""
import json
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"
CHARTS = HERE / "charts"
RESULTS = HERE / "results"
SEED = 20260929
N_PATHS = 10_000
BLOCK = 12  # months per bootstrap block (keeps within-year momentum/crash clustering)

# ---- the saver --------------------------------------------------------------------------------
START_BALANCE = 16_825.0
ANNUAL_CONTRIB = 19_800.0  # 16% employee + 4% match on $99k
MONTHLY_CONTRIB = ANNUAL_CONTRIB / 12
START_MONTH = pd.Period("2026-10", "M")  # age 22
HORIZON_MONTHS = 33 * 12  # to age 55 (~Sep 2059)
AGE0 = 22

# ---- expense ratios (% per year). Plan ERs from the user; fund-class ERs approximate public figures.
# A series is built from a chain of (ticker, that ticker's ER); the first ticker with data wins, and
# each month's return is shifted by (ER_ticker - ER_target)/12 so it reflects the plan's cost.
SERIES = {
    # index building blocks at zero cost (used for A's reconstruction and the CMA model)
    "US_L0": ([("VFIAX", .04), ("VFINX", .14)], 0.0),
    "INTL0": ([("VTSNX", .06), ("VGTSX", .17)], 0.0),
    "MID0": ([("VIMAX", .05), ("VIMSX", .17)], 0.0),
    "SMALL0": ([("VSMAX", .05), ("NAESX", .17)], 0.0),
    "REIT0": ([("VGSLX", .13), ("VGSIX", .27)], 0.0),
    "BOND0": ([("VBTLX", .04), ("VBMFX", .15)], 0.0),
    "CASH0": ([("VFISX", .20)], 0.0),
    # plan funds, net of the plan's ER
    "SP500_SA": ([("VFIAX", .04), ("VFINX", .14)], 0.00),
    "VTSNX": ([("VTSNX", .06), ("VGTSX", .17)], 0.06),
    "VIMAX": ([("VIMAX", .05), ("VIMSX", .17)], 0.05),
    "VSMAX": ([("VSMAX", .05), ("NAESX", .17)], 0.05),
    "NEW_WORLD_R6": ([("RNWGX", .57), ("NEWFX", .97)], 0.57),
    "LCG_III": ([("VIGRX", .17)], 0.25),  # plan-specific fund; proxied by a large-growth index
    "PUTNAM_INTL_VALUE_R6": ([("PNGAX", 1.04)], 0.66),
    "TROWE_VALUE": ([("TRVLX", .73)], 0.57),
    "STABLE_VALUE": ([("VFISX", .20)], 0.30),  # proxy: short-term Treasuries
    "MFS_MIDCAP_GROWTH_R6": ([("OTCKX", .66), ("OTCAX", 1.00)], 0.66),
    "VGSLX": ([("VGSLX", .13), ("VGSIX", .27)], 0.13),
    "VICTORY_SYCAMORE_EV_R6": ([("VETAX", .91), ("VIMSX", .17)], 0.54),
    "AMCENT_SMALL_GROWTH_R6": ([("ANODX", .82), ("ANOIX", 1.17), ("NAESX", .17)], 0.82),
}
B_WEIGHTS = {"SP500_SA": .45, "VTSNX": .35, "VIMAX": .10, "VSMAX": .10}
C_WEIGHTS = {"SP500_SA": .26, "VTSNX": .23, "NEW_WORLD_R6": .16, "VSMAX": .10, "LCG_III": .08,
             "PUTNAM_INTL_VALUE_R6": .05, "VIMAX": .04, "TROWE_VALUE": .03, "STABLE_VALUE": .01,
             "MFS_MIDCAP_GROWTH_R6": .01, "VGSLX": .01, "VICTORY_SYCAMORE_EV_R6": .01,
             "AMCENT_SMALL_GROWTH_R6": .01}
A_ER = 0.09
# LifePath Index 2055 equity sleeve mix (fact sheet 6/30/2026 holdings: R1000 55.91, ACWI-ex-US 37.23,
# small cap 3.52, REIT 1.23) -> normalized. Fixed income modeled as the US aggregate bond index.
A_EQUITY_MIX = {"US_L0": 55.91, "INTL0": 37.23, "SMALL0": 3.52, "REIT0": 1.23}
_tot = sum(A_EQUITY_MIX.values())
A_EQUITY_MIX = {k: v / _tot for k, v in A_EQUITY_MIX.items()}
# Glide path from the prospectus supplement effective ~June 1, 2026 (years to target -> equity incl. REITs).
GLIDE = [(45, .99), (40, .99), (35, .99), (30, .99), (25, .96), (20, .90), (15, .81), (10, .71), (5, .59), (0, .40)]
# Mapping for the CMA model: every plan fund = an index block minus its ER (zero alpha before fees).
FUND_TO_BLOCK = {"SP500_SA": "US_L0", "VTSNX": "INTL0", "VIMAX": "MID0", "VSMAX": "SMALL0",
                 "NEW_WORLD_R6": "INTL0", "LCG_III": "US_L0", "PUTNAM_INTL_VALUE_R6": "INTL0",
                 "TROWE_VALUE": "US_L0", "STABLE_VALUE": "CASH0", "MFS_MIDCAP_GROWTH_R6": "MID0",
                 "VGSLX": "REIT0", "VICTORY_SYCAMORE_EV_R6": "MID0", "AMCENT_SMALL_GROWTH_R6": "SMALL0"}
# Forward-looking real (after-inflation) geometric annual returns. Rounded, own assumptions, set to be
# broadly consistent with published 2026 long-term capital market assumptions (e.g. J.P. Morgan's
# 6.4% nominal for a 60/40) with ~2.5% inflation. Stable value gets a smoothed ~1.2% real.
CMA_REAL = {"US_L0": .042, "MID0": .045, "SMALL0": .048, "INTL0": .050, "REIT0": .040, "BOND0": .020,
            "CASH0": .012}

COLORS = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a", "H1": "#eda100", "H2": "#e87ba4",
          "H3": "#4a3aa7", "A60": "#008300"}
NAMES = {"A": "A  LifePath Index 2055 K", "B": "B  DIY 4-fund index", "C": "C  Old 14-fund mix",
         "A60": "A' LifePath Index 2060 K", "H1": "H1 B, switch to A (2055) at 40",
         "H2": "H2 B, switch to A' (2060) at 40", "H3": "H3 B, glide to 60/40 from 40 to 55"}
TEXT = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"


# ---- data ------------------------------------------------------------------------------------
def load_prices():
    prices = {}
    for path in sorted(RAW.glob("*.json")):
        if path.stem == "CPI":
            continue
        series = json.loads(path.read_text())["Monthly Adjusted Time Series"]
        s = pd.Series({pd.Period(d[:7], "M"): float(v["5. adjusted close"]) for d, v in series.items()})
        prices[path.stem] = s.sort_index()
    return pd.DataFrame(prices)


def load_cpi():
    rows = json.loads((RAW / "CPI.json").read_text())["data"]
    s = pd.Series({pd.Period(r["date"][:7], "M"): float(r["value"]) for r in rows if r["value"] != "."})
    return s.sort_index().pct_change()


# Alpha Vantage omits LIVKX's December 2024 distribution (price -5.3% with no dividend recorded), which
# makes 2024 read 13.65% vs the published 16.29% (BlackRock fact sheet, 6/30/2026). The December return is
# rescaled so the calendar year matches the published figure. Other years match the fact sheet exactly.
CALENDAR_YEAR_FIXES = {("LIVKX", 2024): 0.1629}


def apply_fixes(rets):
    rets = rets.copy()
    for (ticker, year), published in CALENDAR_YEAR_FIXES.items():
        yr = rets.loc[f"{year}-01":f"{year}-12", ticker]
        dec = pd.Period(f"{year}-12", "M")
        others = (1 + yr.drop(dec)).prod()
        rets.loc[dec, ticker] = (1 + published) / others - 1
    return rets


def build_series(rets):
    out = {}
    for name, (chain, target) in SERIES.items():
        s = pd.Series(np.nan, index=rets.index)
        source = pd.Series("", index=rets.index)
        for ticker, er in reversed(chain):  # later (preferred) tickers overwrite earlier fallbacks
            r = rets[ticker] + (er - target) / 100 / 12
            ok = r.notna()
            s[ok] = r[ok]
            source[ok] = ticker
        out[name] = s
        out[name + "__src"] = source
    df = pd.DataFrame(out)
    return df[[c for c in df if not c.endswith("__src")]], df[[c for c in df if c.endswith("__src")]]


def glide_equity(years_to_target):
    ys, eq = zip(*sorted(GLIDE))
    return float(np.interp(years_to_target, ys, eq))  # clamps at 40% past target, 99% beyond 45y


def year_frac(period):
    return period.year + (period.month - 0.5) / 12


def a_weights(period, target_year):
    eq = glide_equity(target_year + 0.5 - year_frac(period))  # target date taken as mid-year
    w = {k: v * eq for k, v in A_EQUITY_MIX.items()}
    w["BOND0"] = 1 - eq
    return w


def a_reconstructed(series, target_year=2055):
    rows = [sum(series.loc[p, k] * v for k, v in a_weights(p, target_year).items()) for p in series.index]
    return pd.Series(rows, index=series.index) - A_ER / 100 / 12


# ---- backtest --------------------------------------------------------------------------------
def run_portfolio(rets, weights, start, contrib):
    """Monthly: grow holdings, add contribution at target weights, rebalance each December."""
    cols = list(weights)
    w = np.array([weights[c] for c in cols])
    r = rets[cols].to_numpy()
    hold = start * w
    values = []
    for i, p in enumerate(rets.index):
        hold = hold * (1 + r[i]) + contrib * w
        if p.month == 12:
            hold = hold.sum() * w
        values.append(hold.sum())
    return pd.Series(values, index=rets.index)


def stats(twr_values, balance, n_contrib, start):
    rets = twr_values.pct_change().fillna(twr_values.iloc[0] - 1)
    years = len(rets) / 12
    idx = twr_values / twr_values.cummax()
    roll12 = (1 + rets).rolling(12).apply(np.prod, raw=True) - 1
    return {
        "CAGR": twr_values.iloc[-1] ** (1 / years) - 1,
        "Volatility": rets.std() * np.sqrt(12),
        "Max drawdown": idx.min() - 1,
        "Worst 12m": roll12.min(),
        "Worst 12m ending": str(roll12.idxmin()),
        "Ending balance": balance.iloc[-1],
        "Contributed": start + n_contrib * MONTHLY_CONTRIB,
    }


def backtest(window_rets, a_series, label):
    frame = window_rets.copy()
    frame["A"] = a_series.reindex(frame.index)
    frame = frame.dropna(subset=["A"] + list(B_WEIGHTS) + list(C_WEIGHTS))
    out, curves, balances = {}, {}, {}
    for key, w in (("A", {"A": 1.0}), ("B", B_WEIGHTS), ("C", C_WEIGHTS)):
        twr = run_portfolio(frame, w, 1.0, 0.0)
        bal = run_portfolio(frame, w, START_BALANCE, MONTHLY_CONTRIB)
        out[key] = stats(twr, bal, len(frame), START_BALANCE)
        curves[key], balances[key] = twr, bal
    out["_window"] = f"{frame.index[0]} to {frame.index[-1]} ({len(frame)} months) [{label}]"
    return out, pd.DataFrame(curves), pd.DataFrame(balances)


# ---- Monte Carlo -----------------------------------------------------------------------------
def horizon_periods():
    return pd.period_range(START_MONTH, periods=HORIZON_MONTHS, freq="M")


def strategy_weights(key, assets):
    """(months x assets) target weight matrix for each strategy; rebalanced monthly in the MC."""
    periods = horizon_periods()
    idx = {a: i for i, a in enumerate(assets)}
    W = np.zeros((len(periods), len(assets)))
    switch_m = (40 - AGE0) * 12

    def put(m, weights, scale=1.0):
        for k, v in weights.items():
            W[m, idx[k]] += v * scale

    for m, p in enumerate(periods):
        age = AGE0 + m / 12
        if key == "A":
            put(m, a_weights(p, 2055))
        elif key == "A60":
            put(m, a_weights(p, 2060))
        elif key == "B":
            put(m, B_WEIGHTS)
        elif key == "C":
            put(m, C_WEIGHTS)
        elif key in ("H1", "H2"):
            if m < switch_m:
                put(m, B_WEIGHTS)
            else:
                put(m, a_weights(p, 2055 if key == "H1" else 2060))
        elif key == "H3":
            eq = 1.0 if age < 40 else 1.0 - 0.40 * min((age - 40) / 15, 1.0)
            put(m, B_WEIGHTS, eq)
            W[m, idx["BOND_FUND"]] += 1 - eq
    return W


def simulate_paths(R, key, assets, override=None):
    """R: (paths x months x assets) real monthly returns. Returns balances (paths x months+1)."""
    W = strategy_weights(key, assets)
    port = np.einsum("pma,ma->pm", R, W)
    if key in ("A", "A60"):
        port -= A_ER / 100 / 12
    elif key in ("H1", "H2"):
        port[:, (40 - AGE0) * 12:] -= A_ER / 100 / 12
    if override is not None:  # (start_month, (months x assets) historical block) for crash tests
        m0, block = override
        W_tail = W[m0:m0 + len(block)]
        tail = (W_tail * block).sum(axis=1)
        if key in ("A", "A60", "H1", "H2"):  # crash blocks sit after age 40, so H1/H2 hold A by then
            tail -= A_ER / 100 / 12
        port[:, m0:m0 + len(block)] = tail
    bal = np.empty((port.shape[0], port.shape[1] + 1))
    bal[:, 0] = START_BALANCE
    for m in range(port.shape[1]):
        bal[:, m + 1] = bal[:, m] * (1 + port[:, m]) + MONTHLY_CONTRIB
    return bal


def bootstrap_indices(rng, n_hist, n_paths, n_months):
    n_blocks = -(-n_months // BLOCK)
    starts = rng.integers(0, n_hist, size=(n_paths, n_blocks))
    offs = np.arange(BLOCK)
    idx = (starts[:, :, None] + offs[None, None, :]) % n_hist  # circular blocks
    return idx.reshape(n_paths, -1)[:, :n_months]


def cma_matrix(real):
    """Index-only real returns with each block's mean shifted to its CMA; funds = block - ER."""
    blocks = {}
    for b, g in CMA_REAL.items():
        x = real[b]
        target_arith = (1 + g) ** (1 / 12) - 1 + x.var() / 2
        blocks[b] = x - x.mean() + target_arith
    out = pd.DataFrame(blocks)
    for fund, block in FUND_TO_BLOCK.items():
        out[fund] = out[block] - SERIES[fund][1] / 100 / 12
    out["BOND_FUND"] = out["BOND0"] - 0.05 / 100 / 12
    return out


def summarize(bal):
    at = lambda age: bal[:, (age - AGE0) * 12]  # noqa: E731
    last5 = bal[:, -61:]
    dd = (last5 / np.maximum.accumulate(last5, axis=1)).min(axis=1) - 1
    b55, b50 = at(55), at(50)
    return {
        "P10 @50": np.percentile(b50, 10), "Median @50": np.median(b50), "P90 @50": np.percentile(b50, 90),
        "P5 @55": np.percentile(b55, 5), "P10 @55": np.percentile(b55, 10), "Median @55": np.median(b55),
        "P90 @55": np.percentile(b55, 90), "Mean @55": b55.mean(),
        "Median worst drop in last 5y": np.median(dd), "P90-bad worst drop in last 5y": np.percentile(dd, 10),
        "P(balance falls >25% from a peak in last 5y)": float((dd < -0.25).mean()),
    }


# ---- charts ----------------------------------------------------------------------------------
def style(ax, title, ylabel):
    ax.set_title(title, loc="left", fontsize=12, color=TEXT, fontweight="bold")
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.tick_params(colors=MUTED)


def money(x, _=None):
    return f"${x/1e6:.1f}M" if abs(x) >= 1e6 else f"${x/1e3:.0f}k"


def end_labels(ax, x, items, log=False, gap_frac=0.045):
    """Label line ends at the right edge, nudging labels apart so they never overlap."""
    lo, hi = ax.get_ylim()
    f = np.log10 if log else (lambda v: v)
    inv = (lambda v: 10 ** v) if log else (lambda v: v)
    gap = (f(hi) - f(lo)) * gap_frac
    placed = []
    for text, y in sorted(items, key=lambda t: t[1]):
        pos = f(y) if not placed else max(f(y), placed[-1] + gap)
        placed.append(pos)
        ax.annotate(text, (x, inv(pos)), xytext=(4, 0), textcoords="offset points", va="center",
                    fontsize=9, color=TEXT, annotation_clip=False)


def plot_curves(curves, title, path):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = curves.index.to_timestamp()
    for k in curves:
        ax.plot(x, curves[k] * 10_000, color=COLORS[k], lw=2, label=NAMES[k])
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(base=10, subs=(1, 2, 5)))
    ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.yaxis.set_major_formatter(plt.FuncFormatter(money))
    end_labels(ax, x[-1], [(f"{k} {money(curves[k].iloc[-1]*10_000)}", curves[k].iloc[-1] * 10_000) for k in curves],
               log=True)
    style(ax, title, "Growth of $10,000 (log scale, net of plan ERs)")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_drawdowns(curves, title, path):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = curves.index.to_timestamp()
    for k in curves:
        ax.plot(x, (curves[k] / curves[k].cummax() - 1) * 100, color=COLORS[k], lw=1.6, label=NAMES[k])
    style(ax, title, "Drawdown from prior peak (%)")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_fan(bal_by_key, keys, title, path):
    fig, axes = plt.subplots(1, len(keys), figsize=(4.2 * len(keys), 4.6), sharey=True)
    ages = AGE0 + np.arange(HORIZON_MONTHS + 1) / 12
    for ax, k in zip(axes, keys):
        b = bal_by_key[k]
        p10, p25, p50, p75, p90 = np.percentile(b, [10, 25, 50, 75, 90], axis=0)
        ax.fill_between(ages, p10, p90, color=COLORS[k], alpha=0.15, lw=0, label="10th-90th pct")
        ax.fill_between(ages, p25, p75, color=COLORS[k], alpha=0.30, lw=0, label="25th-75th pct")
        ax.plot(ages, p50, color=COLORS[k], lw=2, label="Median")
        for v in (p10[-1], p50[-1], p90[-1]):
            ax.annotate(money(v), (ages[-1], v), xytext=(3, 0), textcoords="offset points", va="center",
                        fontsize=8, color=TEXT)
        style(ax, NAMES[k], "Balance, today's dollars" if ax is axes[0] else "")
        ax.set_xlabel("Age", color=MUTED)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(money))
        ax.set_xlim(AGE0, 58.5)
    axes[0].legend(frameon=False, loc="upper left", fontsize=8)
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, fontweight="bold", color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_glide(path):
    periods = horizon_periods()
    ages = AGE0 + np.arange(len(periods)) / 12
    fig, ax = plt.subplots(figsize=(10, 4.2))
    series = {
        "A": [glide_equity(2055.5 - year_frac(p)) for p in periods],
        "A60": [glide_equity(2060.5 - year_frac(p)) for p in periods],
        "B": [1.0] * len(periods),
        "H1": [1.0 if a < 40 else glide_equity(2055.5 - year_frac(p)) for a, p in zip(ages, periods)],
        "H3": [1.0 if a < 40 else 1 - 0.4 * min((a - 40) / 15, 1) for a in ages],
    }
    for k, v in series.items():
        ax.plot(ages, np.array(v) * 100, color=COLORS[k], lw=2, label=NAMES[k])
    style(ax, "Stock share by age (C is ~99% stocks throughout; H1 overlaps A after 40)", "Equity allocation (%)")
    ax.set_xlabel("Age", color=MUTED)
    ax.set_ylim(30, 104)
    ax.legend(frameon=False, loc="lower left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_crash(base, crash, keys, title, path):
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ages = AGE0 + np.arange(HORIZON_MONTHS + 1) / 12
    lo = (45 - AGE0) * 12
    for k in keys:
        ax.plot(ages[lo:], np.median(base[k], axis=0)[lo:], color=COLORS[k], lw=1.2, ls="--", alpha=0.7)
        ax.plot(ages[lo:], np.median(crash[k], axis=0)[lo:], color=COLORS[k], lw=2, label=NAMES[k])
    end_labels(ax, ages[-1], [(f"{k} {money(np.median(crash[k][:, -1]))}", np.median(crash[k][:, -1])) for k in keys])
    ax.axvspan(50, 55, color=GRID, alpha=0.5, lw=0)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(money))
    style(ax, title, "Median balance, today's dollars")
    ax.set_xlabel("Age (dashed = same paths without the crash)", color=MUTED)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_validation(actual, recon, path):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = actual.index.to_timestamp()
    ax.plot(x, (1 + actual).cumprod() * 10_000, color=COLORS["A"], lw=2, label="LIVKX actual")
    ax.plot(x, (1 + recon).cumprod() * 10_000, color=MUTED, lw=1.5, ls="--",
            label="Reconstruction from index proxies + 2026 glide path")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(money))
    style(ax, "Check: does the A reconstruction track the real fund?", "Growth of $10,000")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def write_tables(report):
    pct = lambda v: f"{v*100:.1f}%"  # noqa: E731
    m = lambda v: f"${v/1e6:.2f}M"  # noqa: E731
    lines = []
    for key, title in (("backtest_actual_funds", "Backtest 1: real funds"), ("backtest_long_proxy", "Backtest 2: long window")):
        bt = report[key]
        lines += [f"### {title}", f"Window: {bt['_window']}", "",
                  "| Option | CAGR | Volatility | Max drawdown | Worst 12 months | Ending balance* |",
                  "|---|---|---|---|---|---|"]
        for k in "ABC":
            s_ = bt[k]
            lines.append(f"| {NAMES[k]} | {pct(s_['CAGR'])} | {pct(s_['Volatility'])} | {pct(s_['Max drawdown'])} | "
                         f"{pct(s_['Worst 12m'])} (to {s_['Worst 12m ending']}) | ${s_['Ending balance']:,.0f} |")
        lines += ["", f"*${START_BALANCE:,.0f} start + ${MONTHLY_CONTRIB:,.0f}/month; total contributed "
                  f"${bt['A']['Contributed']:,.0f}. Nominal dollars.", ""]
    for model, mc in report["monte_carlo"].items():
        for scen, title in (("base", "no forced crash"), ("crash_at_50_then_recovery", "2008 crash starts at 50, then 2009-12 recovery"),
                            ("crash_bottoms_at_55", "2008 crash bottoms exactly at 55")):
            lines += [f"### Monte Carlo ({model}): {title}", "",
                      "| Option | P10 @55 | Median @55 | P90 @55 | Median @50 | Median worst drop, last 5y | Bad-case (P10) worst drop, last 5y | P(>25% drop in last 5y) |",
                      "|---|---|---|---|---|---|---|---|"]
            for k, s_ in mc[scen].items():
                lines.append(f"| {NAMES[k]} | {m(s_['P10 @55'])} | {m(s_['Median @55'])} | {m(s_['P90 @55'])} | "
                             f"{m(s_['Median @50'])} | {pct(s_['Median worst drop in last 5y'])} | "
                             f"{pct(s_['P90-bad worst drop in last 5y'])} | {pct(s_['P(balance falls >25% from a peak in last 5y)'])} |")
            lines.append("")
        lines += [f"Head-to-head ({model}): " + ", ".join(f"{k} = {pct(v)}" for k, v in mc.items() if k.startswith("P(")), ""]
    (RESULTS / "summary_tables.md").write_text("\n".join(lines))


# ---- main ------------------------------------------------------------------------------------
def main():
    CHARTS.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    prices = load_prices()
    rets = apply_fixes(prices.pct_change().iloc[1:])
    series, sources = build_series(rets)
    series.to_csv(RESULTS / "monthly_returns_net_of_plan_er.csv")
    report = {"data_through": str(prices.index[-1]), "note": "last month is month-to-date (prices to 2026-09-28)"}

    c_er = sum(SERIES[k][1] * w for k, w in C_WEIGHTS.items())
    b_er = sum(SERIES[k][1] * w for k, w in B_WEIGHTS.items())
    report["weighted_er_pct"] = {"A": A_ER, "B": round(b_er, 4), "C": round(c_er, 4)}

    # A: real fund vs reconstruction check
    a_rec = a_reconstructed(series)
    livkx = rets["LIVKX"].dropna()
    both = pd.concat([livkx, a_rec], axis=1, keys=["actual", "recon"]).dropna()
    diff = both["actual"] - both["recon"]
    report["A_reconstruction_check"] = {
        "window": f"{both.index[0]} to {both.index[-1]}",
        "actual_CAGR": float((1 + both["actual"]).prod() ** (12 / len(both)) - 1),
        "recon_CAGR": float((1 + both["recon"]).prod() ** (12 / len(both)) - 1),
        "tracking_error_ann": float(diff.std() * np.sqrt(12)),
        "correlation": float(both.corr().iloc[0, 1]),
    }
    plot_validation(both["actual"], both["recon"], CHARTS / "a_reconstruction_check.png")

    # Backtest 1: real funds (LIVKX exists from 2011-08)
    bt_real, curves_real, bal_real = backtest(series.loc["2011-08":], livkx, "actual LIVKX; actual fund classes where they exist")
    # Backtest 2: long window with proxies (Jan 2000 -, includes dot-com bust and 2008)
    bt_long, curves_long, bal_long = backtest(series.loc["2000-01":], a_rec, "A reconstructed; older share classes ER-adjusted")
    report["backtest_actual_funds"] = bt_real
    report["backtest_long_proxy"] = bt_long
    # which ticker supplied each series at the start of each window
    report["series_sources"] = {
        k.replace("__src", ""): {"2000-01": sources.loc["2000-01", k], "2011-08": sources.loc["2011-08", k],
                                 "latest": sources.iloc[-1][k]} for k in sources}
    # calendar-year returns (long window, TWR)
    yearly = curves_long.groupby(curves_long.index.year).last()
    yearly = yearly / yearly.shift(1).fillna(1.0) - 1
    yearly.to_csv(RESULTS / "calendar_year_returns_long_window.csv")
    plot_curves(curves_real, "Real funds, Aug 2011 - Sep 2026", CHARTS / "equity_curves_actual_2011_2026.png")
    plot_curves(curves_long, "Long window with proxies, Jan 2000 - Sep 2026", CHARTS / "equity_curves_long_2000_2026.png")
    plot_drawdowns(curves_long, "Drawdowns, Jan 2000 - Sep 2026", CHARTS / "drawdowns_long_2000_2026.png")
    plot_drawdowns(curves_real, "Drawdowns, Aug 2011 - Sep 2026 (real funds)", CHARTS / "drawdowns_actual_2011_2026.png")
    plot_glide(CHARTS / "glide_paths.png")

    # Monte Carlo inputs: real (after-CPI) monthly returns, Jan 2000 - Aug 2026
    cpi = load_cpi()
    hist = series.loc["2000-01":].copy()
    hist["BOND_FUND"] = hist["BOND0"] - 0.05 / 100 / 12
    hist = hist.join(cpi.rename("CPI"), how="inner").dropna()
    real = hist.drop(columns="CPI").apply(lambda c: (1 + c) / (1 + hist["CPI"]) - 1)
    report["mc_history_window"] = f"{real.index[0]} to {real.index[-1]} ({len(real)} months, real)"
    report["historical_real_CAGR"] = {c: float((1 + real[c]).prod() ** (12 / len(real)) - 1)
                                      for c in ["US_L0", "INTL0", "MID0", "SMALL0", "BOND0", "REIT0", "CASH0"]}
    models = {"bootstrap": real, "cma": cma_matrix(real)[real.columns]}
    keys = ["A", "B", "C", "A60", "H1", "H2", "H3"]
    rng = np.random.default_rng(SEED)
    idx = bootstrap_indices(rng, len(real), N_PATHS, HORIZON_MONTHS)  # same draws for every strategy
    assets = list(real.columns)
    crash_full = real.loc["2007-11":"2012-10"].to_numpy()   # 60 months: 2008 crash + recovery
    crash_trough = real.loc["2007-11":"2009-02"].to_numpy()  # 16 months: peak to trough
    report["crash_blocks_real_return"] = {
        "US_L0 Nov07-Feb09": float((1 + real.loc["2007-11":"2009-02", "US_L0"]).prod() - 1),
        "INTL0 Nov07-Feb09": float((1 + real.loc["2007-11":"2009-02", "INTL0"]).prod() - 1),
        "BOND0 Nov07-Feb09": float((1 + real.loc["2007-11":"2009-02", "BOND0"]).prod() - 1),
    }
    mc = {}
    for model, mat in models.items():
        R = mat[assets].to_numpy(dtype=np.float32)[idx]  # paths x months x assets
        base, crash50, crash55 = {}, {}, {}
        for k in keys:
            base[k] = simulate_paths(R, k, assets)
            crash50[k] = simulate_paths(R, k, assets, (HORIZON_MONTHS - 60, crash_full))
            crash55[k] = simulate_paths(R, k, assets, (HORIZON_MONTHS - 16, crash_trough))
        mc[model] = {
            "base": {k: summarize(base[k]) for k in keys},
            "crash_at_50_then_recovery": {k: summarize(crash50[k]) for k in keys},
            "crash_bottoms_at_55": {k: summarize(crash55[k]) for k in keys},
            "P(B beats A @55)": float((base["B"][:, -1] > base["A"][:, -1]).mean()),
            "P(B beats C @55)": float((base["B"][:, -1] > base["C"][:, -1]).mean()),
            "P(H1 beats A @55)": float((base["H1"][:, -1] > base["A"][:, -1]).mean()),
        }
        plot_fan(base, ["A", "B", "C", "H1"], f"Monte Carlo to age 55 ({model}; {N_PATHS:,} seeded paths; today's dollars)",
                 CHARTS / f"mc_fan_{model}.png")
        plot_crash(base, crash55, ["A", "B", "C", "H1", "H3"],
                   f"2008-style crash that bottoms at 55 ({model} model)", CHARTS / f"crash_bottoms_at_55_{model}.png")
        plot_crash(base, crash50, ["A", "B", "C", "H1", "H3"],
                   f"2008-style crash starting at 50, then 2009-12 recovery ({model} model)",
                   CHARTS / f"crash_at_50_{model}.png")
    report["monte_carlo"] = mc
    report["mc_setup"] = {"seed": SEED, "paths": N_PATHS, "block_months": BLOCK, "months": HORIZON_MONTHS,
                          "start_balance": START_BALANCE, "annual_contribution_real": ANNUAL_CONTRIB,
                          "cma_real": CMA_REAL}
    write_tables(report)
    (RESULTS / "results.json").write_text(json.dumps(report, indent=2, default=float))
    print(json.dumps({k: report[k] for k in ["weighted_er_pct", "A_reconstruction_check", "mc_history_window",
                                             "historical_real_CAGR", "crash_blocks_real_return"]}, indent=1, default=float))


if __name__ == "__main__":
    main()
