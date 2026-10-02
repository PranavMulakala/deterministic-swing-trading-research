# Stocks that have moved like LITE: big, liquid, strongly trending, with large daily swings (October 2, 2026)

Screen of the daily prices already on disk: 5,259 US stocks, through Sept 28, 2026. Code: `research/lite_like_screener_v1/screen.py`. S&P 500 membership comes from Wikipedia's list, downloaded Oct 2.

**This is a description of the past, not a buy list.** Every stock here was picked *because* it already went up a lot. Nothing in this table says what happens next, and every one of them had a large drop (−12% to −74%) inside the same year.

## The filters
| What you asked for | Rule used |
|---|---|
| Big, well-known company | **$300M+ traded per day**, price $20+ (and an S&P 500 flag) |
| "Big sweeping moves through the day" | Average **daily range** (high − low) of **3%+** over the last 60 days |
| "A year or two of big moves" | **Up 50%+ over the last year** (2-year return also shown) |

## How to read the columns
- **Avg open gap:** how far it typically opens from the previous close.
- **1%+ dip days:** share of days in the last year that traded at least 1% below the open at some point.
- **Dips that closed ≥ open:** of those dip days, how often it finished the day back at or above the open. For LITE it's 40%: on most dip days, it closed lower.

## LITE's own row, for comparison
+479% in 1 year, 7.5% average daily range, worst drop −43%, $3.9B traded per day.

## Closest matches to LITE (S&P 500, semiconductors / AI hardware, daily range 5%+)
| Stock | 1-yr | Daily range | Worst drop (1 yr) |
|---|---|---|---|
| MU (Micron) | +573% | 5.4% | −39% |
| SNDK (Sandisk) | +1,717% | 7.9% | −56% |
| WDC (Western Digital) | +324% | 6.4% | −45% |
| STX (Seagate) | +323% | 6.3% | −32% |
| DELL | +320% | 6.3% | −32% |
| INTC (Intel) | +241% | 5.3% | −42% |
| TER (Teradyne) | +203% | 5.6% | −34% |
| MRVL (Marvell) | +201% | 5.7% | −48% |
| COHR (Coherent) | +165% | 7.1% | −48% |
| CIEN (Ciena) | +151% | 6.0% | −49% |
| HPE | +163% | 5.5% | −26% |

## What this means
1. **These are all the same trade.** Almost every LITE-like stock is AI hardware: memory, storage, optics, chips. If AI spending slows, they will likely fall together, like LITE −43% and MU −39% this summer.
2. **"Bound to go up" doesn't exist.** Research does find that stocks that rose over the past year tend to keep rising slightly more than average ("momentum"), but that effect is small and suffers sudden crashes. It's a tilt, not a guarantee.
3. **Big daily swings cut both ways.** A 6–8% average daily range means $6,000–$8,000 of movement in a typical day on a $100k position.
4. **For the LITE dip bot:** these are candidates for a future paper test of the same dip rule, after the 8-week test ends (formula freeze).

## Full table (69 stocks)
69 of 386 big, liquid stocks (price ≥ $20, ≥ $300M traded a day) passed: up ≥ 50% in a year and an average daily range ≥ 3%.

| # | Stock | S&P 500 | Industry | Price | 1-yr | 2-yr | Avg daily range | Avg open gap | Worst drop (1 yr) | $ volume/day | 1%+ dip days | Dips that closed ≥ open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **SNDK** Sandisk | yes | Technology Hardware, Storage & Peripherals | $1,712.89 | 1,717% | n/a% | 7.9% | 3.6% | -56% | $20,505M | 75% | 36% |
| 2 | **AXTI**  | no | - | $73.67 | 1,451% | 3,584% | 11.4% | 4.7% | -74% | $661M | 86% | 44% |
| 3 | **MRNA** Moderna | yes | Biotechnology | $197.28 | 702% | 208% | 8.5% | 3.1% | -34% | $2,414M | 75% | 42% |
| 4 | **MU** Micron Technology | yes | Semiconductors | $1,053.98 | 573% | 1,033% | 5.4% | 2.8% | -39% | $31,669M | 74% | 34% |
| 5 | **LITE** Lumentum | yes | Communications Equipment | $921.32 | 479% | 1,405% | 7.5% | 2.8% | -43% | $3,891M | 82% | 40% |
| 6 | **RVMD**  | no | - | $201.74 | 375% | 373% | 3.8% | 0.7% | -25% | $380M | 66% | 38% |
| 7 | **WDC** Western Digital | yes | Technology Hardware, Storage & Peripherals | $453.23 | 324% | 909% | 6.4% | 3.1% | -45% | $3,510M | 73% | 35% |
| 8 | **STX** Seagate Technology | yes | Technology Hardware, Storage & Peripherals | $921.51 | 323% | 797% | 6.3% | 3.0% | -32% | $3,810M | 73% | 35% |
| 9 | **DELL** Dell Technologies | yes | Technology Hardware, Storage & Peripherals | $543.43 | 320% | 377% | 6.3% | 1.9% | -32% | $3,749M | 69% | 31% |
| 10 | **DOCN**  | no | - | $136.29 | 288% | 232% | 7.5% | 2.0% | -42% | $379M | 77% | 37% |
| 11 | **ASX**  | no | - | $43.79 | 285% | 353% | 4.0% | 2.7% | -31% | $303M | 55% | 29% |
| 12 | **BE** Bloom Energy | yes | Electrical Components & Equipment | $262.87 | 283% | 2,321% | 8.6% | 3.6% | -53% | $3,624M | 87% | 43% |
| 13 | **AMD** Advanced Micro Devices | yes | Semiconductors | $607.87 | 277% | 288% | 4.7% | 2.4% | -28% | $12,407M | 69% | 35% |
| 14 | **AAOI**  | no | - | $96.82 | 268% | 589% | 8.9% | 3.5% | -66% | $1,080M | 86% | 44% |
| 15 | **INTC** Intel | yes | Semiconductors | $116.03 | 241% | 414% | 5.3% | 2.5% | -42% | $10,973M | 75% | 35% |
| 16 | **TSEM**  | no | - | $226.04 | 231% | 436% | 6.6% | 3.0% | -41% | $431M | 75% | 34% |
| 17 | **TER** Teradyne | yes | Semiconductor Materials & Equipment | $401.30 | 203% | 211% | 5.6% | 3.0% | -34% | $1,092M | 68% | 39% |
| 18 | **MRVL** Marvell Technology | yes | Semiconductors | $251.90 | 201% | 253% | 5.7% | 3.2% | -48% | $4,999M | 74% | 39% |
| 19 | **ILMN** Illumina, Inc. | yes | Life Sciences Tools & Services | $271.90 | 195% | 109% | 4.3% | 0.8% | -26% | $570M | 63% | 33% |
| 20 | **GH**  | no | - | $177.33 | 195% | 655% | 4.7% | 1.1% | -33% | $334M | 76% | 38% |
| 21 | **SMTC**  | no | - | $174.78 | 184% | 278% | 6.8% | 3.1% | -41% | $422M | 79% | 40% |
| 22 | **TWLO**  | no | - | $286.98 | 183% | 355% | 5.0% | 1.6% | -25% | $521M | 70% | 41% |
| 23 | **HUT**  | no | - | $92.71 | 166% | 701% | 8.6% | 2.9% | -42% | $430M | 84% | 45% |
| 24 | **COHR** Coherent Corp. | yes | Electronic Components | $282.45 | 165% | 220% | 7.1% | 3.2% | -48% | $1,870M | 80% | 38% |
| 25 | **HPE** Hewlett Packard Enterprise | yes | Technology Hardware, Storage & Peripherals | $62.63 | 163% | 248% | 5.5% | 1.8% | -26% | $1,078M | 67% | 25% |
| 26 | **NTRA**  | no | - | $411.77 | 152% | 233% | 3.7% | 1.1% | -28% | $432M | 62% | 38% |
| 27 | **CIEN** Ciena | yes | Communications Equipment | $344.19 | 151% | 458% | 6.0% | 2.3% | -49% | $850M | 78% | 44% |
| 28 | **LRCX** Lam Research | yes | Semiconductor Materials & Equipment | $314.47 | 147% | 307% | 4.8% | 3.1% | -42% | $3,003M | 66% | 36% |
| 29 | **AMAT** Applied Materials | yes | Semiconductor Materials & Equipment | $486.76 | 145% | 155% | 4.4% | 2.8% | -42% | $3,730M | 62% | 31% |
| 30 | **ATI**  | no | - | $180.67 | 133% | 178% | 4.0% | 1.2% | -22% | $334M | 67% | 32% |
| 31 | **VLO** Valero Energy | yes | Oil & Gas Refining & Marketing | $389.57 | 128% | 204% | 3.6% | 1.0% | -12% | $1,054M | 65% | 32% |
| 32 | **TTMI**  | no | - | $124.19 | 128% | 582% | 6.6% | 2.7% | -54% | $316M | 81% | 37% |
| 33 | **MTSI**  | no | - | $278.56 | 125% | 160% | 5.0% | 2.3% | -44% | $392M | 72% | 37% |
| 34 | **OKTA**  | no | - | $202.18 | 122% | 165% | 5.2% | 1.6% | -34% | $571M | 65% | 36% |
| 35 | **CRWD** CrowdStrike | yes | Systems Software | $259.25 | 119% | 254% | 5.2% | 1.3% | -37% | $2,110M | 67% | 36% |
| 36 | **NBIS**  | no | - | $231.88 | 115% | 1,124% | 8.6% | 3.2% | -48% | $4,386M | 81% | 35% |
| 37 | **FIX** Comfort Systems USA | yes | Construction & Engineering | $1,658.30 | 113% | 330% | 4.5% | 2.1% | -26% | $705M | 71% | 37% |
| 38 | **MKSI**  | no | - | $258.38 | 112% | 139% | 4.7% | 2.9% | -48% | $400M | 71% | 36% |
| 39 | **FTNT** Fortinet | yes | Systems Software | $176.33 | 112% | 128% | 4.2% | 1.0% | -14% | $773M | 57% | 31% |
| 40 | **KEYS** Keysight Technologies | yes | Electronic Equipment & Instruments | $359.74 | 109% | 137% | 3.1% | 1.4% | -21% | $409M | 56% | 28% |
| 41 | **FCX** Freeport-McMoRan | yes | Copper | $71.96 | 106% | 64% | 3.5% | 1.9% | -24% | $929M | 69% | 34% |
| 42 | **MPC** Marathon Petroleum | yes | Oil & Gas Refining & Marketing | $389.44 | 102% | 147% | 3.3% | 1.0% | -18% | $910M | 56% | 27% |
| 43 | **ARM**  | no | - | $283.33 | 101% | 100% | 6.2% | 3.0% | -49% | $1,473M | 74% | 34% |
| 44 | **FLEX** Flex Ltd. | yes | Electronic Manufacturing Services | $113.04 | 100% | 245% | 4.9% | 2.3% | -36% | $447M | 71% | 35% |
| 45 | **DDOG** Datadog | yes | Application Software | $268.70 | 97% | 131% | 5.1% | 1.7% | -49% | $1,067M | 69% | 30% |
| 46 | **PANW** Palo Alto Networks | yes | Systems Software | $392.09 | 94% | 128% | 4.8% | 1.2% | -36% | $2,273M | 64% | 30% |
| 47 | **GLW** Corning Inc. | yes | Electronic Components | $151.59 | 93% | 250% | 5.2% | 2.8% | -51% | $1,648M | 69% | 36% |
| 48 | **STM**  | no | - | $52.74 | 88% | 93% | 3.2% | 2.5% | -40% | $528M | 56% | 27% |
| 49 | **PSX** Phillips 66 | yes | Oil & Gas Refining & Marketing | $253.55 | 88% | 107% | 3.1% | 1.1% | -17% | $680M | 52% | 26% |
| 50 | **KLAC** KLA Corporation | yes | Semiconductor Materials & Equipment | $189.17 | 80% | 152% | 4.5% | 2.7% | -44% | $2,062M | 65% | 34% |
| 51 | **CAT** Caterpillar Inc. | yes | Construction Machinery & Heavy Transportation Equipment | $819.95 | 78% | 126% | 3.1% | 1.5% | -27% | $2,291M | 56% | 26% |
| 52 | **ALAB**  | no | - | $351.31 | 75% | 593% | 7.4% | 3.1% | -56% | $1,342M | 78% | 37% |
| 53 | **VRT** Vertiv | yes | Electrical Components & Equipment | $244.04 | 75% | 155% | 4.9% | 2.5% | -41% | $1,423M | 73% | 32% |
| 54 | **NTAP** NetApp | yes | Technology Hardware, Storage & Peripherals | $204.41 | 72% | 73% | 4.1% | 0.9% | -22% | $468M | 58% | 25% |
| 55 | **SN**  | no | - | $181.99 | 72% | 74% | 3.7% | 0.8% | -26% | $310M | 65% | 27% |
| 56 | **NVT**  | no | - | $160.50 | 67% | 132% | 4.1% | 1.9% | -27% | $347M | 67% | 32% |
| 57 | **CRS**  | no | - | $385.30 | 66% | 146% | 3.9% | 1.2% | -38% | $361M | 71% | 34% |
| 58 | **ENTG**  | no | - | $150.63 | 64% | 36% | 5.0% | 2.8% | -42% | $336M | 75% | 42% |
| 59 | **NET**  | no | - | $353.99 | 62% | 313% | 5.5% | 1.3% | -37% | $1,029M | 74% | 37% |
| 60 | **PWR** Quanta Services | yes | Construction & Engineering | $644.36 | 61% | 118% | 3.5% | 1.5% | -29% | $662M | 65% | 30% |
| 61 | **TXN** Texas Instruments | yes | Semiconductors | $278.31 | 57% | 44% | 3.1% | 1.5% | -23% | $1,837M | 54% | 20% |
| 62 | **GEV** GE Vernova | yes | Heavy Electrical Equipment | $949.77 | 57% | 279% | 4.1% | 1.8% | -26% | $2,386M | 70% | 27% |
| 63 | **HUM** Humana | yes | Managed Health Care | $389.63 | 55% | 28% | 3.5% | 0.6% | -45% | $467M | 58% | 31% |
| 64 | **P** Everpure | yes | Technology Hardware, Storage & Peripherals | $129.40 | 55% | 158% | 5.7% | 1.6% | -42% | $446M | 72% | 33% |
| 65 | **RKLB**  | no | - | $72.19 | 55% | 855% | 6.0% | 1.9% | -61% | $1,353M | 81% | 40% |
| 66 | **MPWR** Monolithic Power Systems | yes | Semiconductors | $1,351.20 | 53% | 54% | 4.3% | 2.2% | -32% | $1,019M | 65% | 30% |
| 67 | **SLB** Schlumberger | yes | Oil & Gas Equipment & Services | $51.49 | 53% | 27% | 3.0% | 0.8% | -22% | $643M | 58% | 23% |
| 68 | **ON** ON Semiconductor | yes | Semiconductors | $75.65 | 52% | 8% | 4.2% | 2.1% | -50% | $784M | 69% | 32% |
| 69 | **JBL** Jabil | yes | Electronic Manufacturing Services | $318.93 | 52% | 183% | 3.7% | 1.6% | -26% | $345M | 62% | 31% |
