# VT 80 + AVUV 20 vs VT 100: verdict **ADOPT**

- Rule 1 forward median >= VT: **PASS** ($575,317 vs $564,168)
- Rule 2 no-premium cost < 3%: **PASS** (-0.1%)
- Rule 3 since-2008 $ drop <= 1.10x VT: **PASS** (-$49,735 vs -$52,662 (0.94x))

Proxy check (2019-11+, 83 months): AVUV 14.7%/yr vs DFSVX 13.5%/yr, correlation 0.993, tracking error 3.6%/yr

### 2020-01 to 2026-09 (81 months) [MAIN: post-COVID; AVUV actual all window]

| Option | Ending (of $ in) | CAGR | Worst drop | Worst drop $ | Worst month $ | Worst 12m $ | Months up |
|---|---|---|---|---|---|---|---|
| VT (one fund) | $88,105 (of $51,158) | 12.5% | -25.5% | -$4,295 | -$4,853 (2026-03) | -$5,648 | 63% |
| VT 80 + AVUV 20 | $88,793 (of $51,158) | 13.0% | -23.9% | -$3,658 | -$4,216 (2026-03) | -$5,298 | 63% |
| VT 80 + QQQM 20 (Reddit-style tilt) | $93,195 (of $51,158) | 14.4% | -26.9% | -$4,246 | -$4,804 (2026-03) | -$5,983 | 64% |

### 2008-08 to 2026-09 (218 months) [stress (decides rule 3): DFSVX before Oct 2019]

| Option | Ending (of $ in) | CAGR | Worst drop | Worst drop $ | Worst month $ | Worst 12m $ | Months up |
|---|---|---|---|---|---|---|---|
| VT (one fund) | $407,534 (of $127,593) | 9.0% | -43.4% | -$52,662 | -$23,288 (2026-03) | -$44,518 | 62% |
| VT 80 + AVUV 20 | $416,684 (of $127,593) | 9.4% | -44.9% | -$49,735 | -$23,392 (2020-03) | -$41,338 | 64% |
| VT 80 + QQQM 20 (Reddit-style tilt) | $497,059 (of $127,593) | 10.8% | -42.7% | -$67,221 | -$26,570 (2026-03) | -$56,457 | 64% |

### 2000-01 to 2026-09 (321 months) [deep stress: VT = today's-mix proxy before 2008]

| Option | Ending (of $ in) | CAGR | Worst drop | Worst drop $ | Worst month $ | Worst 12m $ | Months up |
|---|---|---|---|---|---|---|---|
| VT (one fund) | $861,301 (of $185,058) | 7.3% | -53.8% | -$123,834 | -$48,433 (2026-03) | -$99,307 | 62% |
| VT 80 + AVUV 20 | $899,008 (of $185,058) | 8.1% | -54.4% | -$119,752 | -$55,579 (2020-03) | -$93,448 | 61% |
| VT 80 + QQQM 20 (Reddit-style tilt) | $1,062,349 (of $185,058) | 7.7% | -54.5% | -$156,899 | -$56,025 (2026-03) | -$126,733 | 62% |

### Monte Carlo to 55 (today's dollars)

| Model | Option | P10 | Median | P90 | Median worst drop |
|---|---|---|---|---|---|
| no premium (4.3%) | VT (one fund) | $242,648 | $564,168 | $1,372,653 | -45.6% |
| no premium (4.3%) | VT 80 + AVUV 20 | $240,800 | $563,633 | $1,388,288 | -46.0% |
| no premium (4.3%) | VT 80 + QQQM 20 (Reddit-style tilt) | $230,821 | $575,589 | $1,480,196 | -47.2% |
| bootstrap (info) | VT (one fund) | $241,152 | $560,129 | $1,361,849 | -45.6% |
| bootstrap (info) | VT 80 + AVUV 20 | $279,060 | $669,874 | $1,670,985 | -45.5% |
| bootstrap (info) | VT 80 + QQQM 20 (Reddit-style tilt) | $244,555 | $616,818 | $1,599,148 | -47.0% |
| base (4.8%) | VT (one fund) | $242,648 | $564,168 | $1,372,653 | -45.6% |
| base (4.8%) | VT 80 + AVUV 20 | $244,832 | $575,317 | $1,419,489 | -45.9% |
| base (4.8%) | VT 80 + QQQM 20 (Reddit-style tilt) | $230,821 | $575,589 | $1,480,196 | -47.2% |
| +1 pt (5.8%) | VT (one fund) | $242,648 | $564,168 | $1,372,653 | -45.6% |
| +1 pt (5.8%) | VT 80 + AVUV 20 | $253,294 | $599,248 | $1,482,523 | -45.8% |
| +1 pt (5.8%) | VT 80 + QQQM 20 (Reddit-style tilt) | $230,821 | $575,589 | $1,480,196 | -47.2% |

### Correlation with LITE and MU (monthly)

```
{
 "AVUV actual since 2019-11": {
  "LITE": {
   "AVUV": 0.31,
   "VT": 0.33,
   "QQQ": 0.32
  },
  "MU": {
   "AVUV": 0.38,
   "VT": 0.51,
   "QQQ": 0.53
  }
 },
 "small value (DFSVX) since 2016-01": {
  "LITE": {
   "DFSVX": 0.34,
   "VT": 0.33,
   "QQQ": 0.37
  },
  "MU": {
   "DFSVX": 0.42,
   "VT": 0.5,
   "QQQ": 0.53
  }
 }
}
```
