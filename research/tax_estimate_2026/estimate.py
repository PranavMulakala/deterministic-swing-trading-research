"""2026 tax estimate for a single filer in Georgia (not tax advice; check with a CPA or tax software).

  python3 research/tax_estimate_2026/estimate.py --wages 92250 --short-gains 55000 --long-gains 0 --pretax-401k 0 --interest 0

Federal: IRS Rev. Proc. 2025-32 (2026 brackets, $16,100 standard deduction, 0% long-term gains up to $49,450).
Georgia: DOR "Important Tax Updates" (flat 4.99% for 2026, $15,000 standard deduction); gains are taxed as ordinary income.
FICA: 6.2% Social Security (2026 wage base $184,500) + 1.45% Medicare, on wages including 401(k) deferrals.
Ignores: credits, itemizing, HSA, state/local extras, AMT, and the 3.8% NIIT (only applies above $200k MAGI).
"""
import argparse
import json

BRACKETS = [(12_400, .10), (50_400, .12), (105_700, .22), (201_775, .24), (256_225, .32), (640_600, .35), (float("inf"), .37)]
STD, GA_STD, GA_RATE, LT0, LT15 = 16_100, 15_000, 0.0499, 49_450, 545_500


def ordinary_tax(x):
    tax, low = 0.0, 0.0
    for top, rate in BRACKETS:
        if x > low:
            tax += (min(x, top) - low) * rate
        low = top
    return tax


def estimate(wages, short_gains=0.0, long_gains=0.0, pretax_401k=0.0, interest=0.0):
    net_long = long_gains
    ordinary_income = wages - pretax_401k + short_gains + interest
    if net_long < 0:  # net capital losses offset ordinary income up to $3,000
        ordinary_income += max(net_long, -3_000)
        net_long = 0.0
    agi = ordinary_income + net_long
    taxable = max(agi - STD, 0.0)
    ordinary_taxable = max(taxable - net_long, 0.0)
    fed_ord = ordinary_tax(ordinary_taxable)
    lt_in_0 = max(min(net_long, LT0 - ordinary_taxable), 0.0)
    lt_in_20 = max(ordinary_taxable + net_long - max(LT15, ordinary_taxable), 0.0)
    fed_lt = (net_long - lt_in_0 - lt_in_20) * 0.15 + lt_in_20 * 0.20
    ga = max(agi - GA_STD, 0.0) * GA_RATE
    fica = min(wages, 184_500) * 0.062 + wages * 0.0145
    return {"agi": round(agi), "federal_taxable": round(taxable), "federal_income_tax": round(fed_ord + fed_lt),
            "georgia_income_tax": round(ga), "income_tax_total": round(fed_ord + fed_lt + ga), "fica": round(fica),
            "all_in": round(fed_ord + fed_lt + ga + fica)}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("wages", "short-gains", "long-gains", "pretax-401k", "interest"):
        p.add_argument(f"--{name}", type=float, default=0.0)
    a = p.parse_args()
    print(json.dumps(estimate(a.wages, a.short_gains, a.long_gains, a.pretax_401k, a.interest), indent=1))
