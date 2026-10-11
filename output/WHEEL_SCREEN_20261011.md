# Wheel candidate screen, as of Oct 2, 2026 close (run Oct 11, 2026)

Research only, not a buy list. The decision is the owner's. Made by `research/wheel_screen_v1/screen.py --as-of latest --options`.

## Filters
- common stock, raw price ≤ $500;
- 60-day average dollar volume ≥ $200M;
- close > 50-day > 200-day average;
- 2026 return ≥ +30%;
- within 15% of the 52-week high.

**68 stocks passed.** Below are the 30 most volatile.

## Columns
- **Weekly options:** 3 = weekly expirations exist (Oct 16/23/30); 1 = monthly only, which doesn't fit a ~1-week wheel.
- **Est. fee/wk per $50k:** a rough estimate for a ~1-week 0.30-delta put (≈ 0.03 × volatility). It uses realized volatility; real option prices differ.
- **1 contract needs:** the cash to secure one put (100 shares × price).

| Stock | Price | 1 contract needs | 2026 return | From 52-wk high | Volatility | Est. fee/wk per $50k | Weekly options | Fits $25k? |
|---|---|---|---|---|---|---|---|---|
| MRNA (Moderna) | $190.01 | $19,001 | +544% | -9.0% | 229% | $3,437 | yes | yes |
| SMTC (Semtech Corporation) | $194.88 | $19,488 | +164% | -3.5% | 94% | $1,409 | yes | yes |
| TWST (Twist Bioscience Corporati) | $188.67 | $18,867 | +495% | -5.8% | 88% | $1,325 | no (monthly) | yes |
| OKTA (Okta) | $211.49 | $21,149 | +145% | -2.4% | 75% | $1,128 | yes | yes |
| TER (Teradyne) | $449.04 | $44,904 | +132% | -8.0% | 75% | $1,131 | yes | no |
| RBRK (Rubrik) | $118.58 | $11,858 | +55% | -0.2% | 72% | $1,084 | yes | yes |
| CRWD (CrowdStrike Holdings) | $270.04 | $27,004 | +130% | -1.3% | 71% | $1,062 | yes | no |
| ENTG (Entegris) | $166.47 | $16,647 | +98% | -11.0% | 71% | $1,067 | no (monthly) | yes |
| P (Everpure) | $140.14 | $14,014 | +109% | -0.5% | 70% | $1,050 | no (monthly) | yes |
| DDOG (Datadog) | $277.22 | $27,722 | +104% | -5.3% | 69% | $1,035 | yes | no |
| TWLO (Twilio) | $294.58 | $29,458 | +107% | -3.7% | 68% | $1,021 | yes | no |
| PBF (PBF ENERGY INC.) | $80.78 | $8,078 | +198% | -3.1% | 67% | $1,010 | no (monthly) | yes |
| UMC (United Microelectronic Cor) | $26.27 | $2,627 | +234% | -9.3% | 65% | $975 | no (monthly) | yes |
| HPE (Hewlett Packard Enterprise) | $69.33 | $6,933 | +189% | -1.4% | 64% | $959 | yes | yes |
| ASX (ASE Technology Holding Co.) | $47.45 | $4,745 | +195% | -1.0% | 62% | $932 | no (monthly) | yes |
| LSCC (Lattice Semiconductor Corp) | $134.00 | $13,400 | +82% | -14.7% | 62% | $935 | no (monthly) | yes |
| SWKS (Skyworks Solutions) | $85.03 | $8,503 | +34% | -8.4% | 60% | $900 | no (monthly) | yes |
| PANW (Palo Alto Networks) | $403.24 | $40,324 | +119% | -1.5% | 58% | $868 | yes | no |
| ZETA (Zeta Global Holdings Corp.) | $32.63 | $3,263 | +60% | -0.5% | 58% | $864 | yes | yes |
| NET (Cloudflare) | $349.07 | $34,907 | +77% | -5.0% | 57% | $854 | yes | no |
| ZBRA (Zebra Technologies Corpora) | $375.86 | $37,586 | +55% | -2.7% | 57% | $848 | no (monthly) | no |
| GTLB (GitLab) | $49.78 | $4,978 | +33% | -10.4% | 54% | $805 | yes | yes |
| NTRA (Natera) | $410.35 | $41,035 | +79% | -4.0% | 52% | $784 | no (monthly) | no |
| HPQ (HP) | $32.12 | $3,212 | +44% | -11.3% | 51% | $763 | yes | yes |
| NVT (nVent Electric plc Ordinar) | $169.56 | $16,956 | +66% | -8.2% | 51% | $768 | no (monthly) | yes |
| CNH (CNH INDUSTRIAL N.V.) | $13.47 | $1,347 | +46% | -6.8% | 49% | $732 | no (monthly) | yes |
| SCCO (Southern Copper Corporatio) | $205.54 | $20,554 | +43% | -8.2% | 48% | $718 | yes | yes |
| ANET (Arista Networks) | $207.35 | $20,735 | +58% | -3.5% | 47% | $711 | yes | yes |
| ILMN (Illumina) | $273.04 | $27,304 | +108% | -2.5% | 47% | $698 | no (monthly) | no |
| SNOW (Snowflake) | $341.04 | $34,104 | +56% | -11.3% | 47% | $711 | yes | no |

## Read this before picking
- **A big 2026 return is the *filter*, not a promise.** Tests #17 and #19 showed last year's hottest stocks are often next year's crashes; the screen only finds what is moving now.
- **High fees mean high risk.** MRNA's 229% volatility comes with a stock that can halve in a week; it's biotech news risk.
- **The wheel rule that held up** is "calls never below what you paid." It means you may hold a falling stock for months, so pick only stocks you'd hold through a 40% drop.
- **Earnings:** skip weeks with an earnings report inside them (most of these report late Oct – mid Nov).
