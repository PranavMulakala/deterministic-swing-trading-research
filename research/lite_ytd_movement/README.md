# LITE 2026 movement, data-source and hosting brief

Prepared September 6, 2026. Calendar-year-to-date, as confirmed by the owner.
**Exploratory price descriptions, not a strategy backtest or news-adjusted result.**
Proposed research balance: $5,000. No account/configuration balance changed.

## Measured price coverage and definitions

- January 2–September 4: 170 complete regular sessions, 78 five-minute bars each.
- Pinned raw SIP source: `../lite_execution_data/runs/sip-bars-01/LITE_5Min.json`.
- Source SHA-256: `41fd6ae0f253904f59ff79b275bae0bf4543b114708ff04dc73ffd1da230e183`.
- Original calendar/news SHA-256: `42342bcebbc42da4c51b028b15c90ce8942809566c14c69a841f6cb55e1202a5`.
- Input hashes are checked against the existing manifest/frozen configuration before analysis.
- Opening price is the 09:30 bar open. Closing price is the 15:55 bar close, not
  the 15:55 bar open, an official closing-auction price, or the last after-hours trade.
- Every percentage in the first table is relative to that same day's opening price,
  not the prior close. High/low counts overlap and do not establish movement order.
- Completeness is assessed retrospectively. It must not become a live signal filter.

## How often did LITE move up and down?

| Excursion from opening price | Reached at least this much above open | Reached at least this much below open | Did both, in either order |
|---|---:|---:|---:|
| 1% | 139/170 (81.8%) | 144/170 (84.7%) | 113/170 (66.5%) |
| 2% | 113/170 (66.5%) | 120/170 (70.6%) | 63/170 (37.1%) |
| 3% | 93/170 (54.7%) | 99/170 (58.2%) | 30/170 (17.6%) |
| 5% | 59/170 (34.7%) | 61/170 (35.9%) | 7/170 (4.1%) |

Closed above open: **83/170 (48.8%)**. Below: **87/170 (51.2%)**. Unchanged: zero.
Median high-low range / open: **7.67%**. Median open-to-close return: **-0.22%**.
Best open-to-close: April 2, **+16.74%**. Worst: August 10, **-12.59%**.
These are observed price changes, not obtainable low-to-high trading returns.

## Did an opening dip subsequently recover?

Dip definition: the low during 09:30–09:59:59 was at least 1% below the opening price.
There were **131/170** such sessions. Among them:

- 89/131 (67.9%) traded at or above the opening price at some point from 10:00 onward.
- Only 53/131 (40.5%) finished the regular-session bars at or above the opening price.
- On 46 of those 131 sessions, the 10:00 opening reference was already at/above the
  day's open. Including those days overstates the opportunity to buy at 10:00 and
  wait for a recovery to that target.
- Restricting to the **85 sessions still below the opening price at 10:00**, only
  **43/85 (50.6%)** subsequently reached the day's opening price that same session.
- The remaining **42** did not reach that target after 10:00 before that day's close.

The 10:00 opening price is a descriptive reference, not a guaranteed executable fill.
The target here is the known 09:30 opening price, not an unspecified owner target.

### Longer waits: raw regular-session price-level diagnostic

| Deadline, including the original session | Reached opening-price target | Excluded origins lacking a full observation window |
|---|---:|---:|
| Same session | 43/85 (50.6%) | 0 |
| End of next session | 57/85 (67.1%) | 0 |
| End of fifth subsequent session | 73/82 (89.0%) | 3 |
| End of twentieth subsequent session | 70/73 (95.9%) | 12 |

Denominators differ. All origins without a full horizon are excluded even if they
recovered early; we do not condition coverage on successful outcomes. Do not present
these as 85 independent funded trades or as a 95.9% profitable trading strategy.
This diagnostic does not reconcile corporate actions/dividends, simulate liquidity,
costs or fills, or fund overlapping positions. It checks raw regular-session highs
only, not extended-hours target touches. Already-seen data and LITE's selection
after strong performance remain material limitations.

Three targets were not revisited after the 10:00 reference by the snapshot end:

| Origin | Opening-price target | Subsequent sessions observed |
|---|---:|---:|
| June 3 | $1,028.16 | 65 |
| August 28 | $941.34 | 5 |
| September 1 | $901.04 | 3 |

The June 15 target took **40 subsequent sessions**, until August 12, to reappear.
June 16's took 39 sessions. Unresolved is not a prediction of permanent non-recovery.

For the June 3 unresolved example, the raw 10:00 reference was $960.82. The lowest
subsequent regular-session bar low through September 4 was $594.84 (**-38.09%**), and
the last regular-session bar close was $881.45 (**-8.26%**). This is an unfunded raw
price-path illustration, not a corporate-action-adjusted portfolio result. The
former report's $879.90 reference is the cached last after-hours price, not this
regular-session closing-bar value.

## News and sentiment: precisely what is missing

The cache has **228 unique Benzinga article IDs**, with **119 updated after their
creation timestamp**. It has URLs, timestamps, source and symbol tags, but no
headline, original text or first-received timestamp. All daily sentiment labels
in this study are `unknown`; no headline inference is made from URL slugs.

Next data step: request permitted headline/content fields from the news API, retain
all pages and timestamps, and label fetched historical versions as retrospective.
Do not assume current text existed at publication time, even if a provider reports
an unchanged update timestamp. Live capture should retain each version, receipt
time, source, content hash, event category, symbol relevance and classification
version. A 24/7 collector will improve this evidence prospectively; it cannot
reconstruct a missing original January article or its delivery latency.

Evaluate the same price rules with and without a predeclared news filter. Never
use an afternoon explanatory story as an input to a morning trade. Positive tone
is not a promise of a price increase; earnings surprises and guidance relative to
expectations require additional point-in-time data. No news found means unknown,
not neutral. Syndicated stories should be grouped into events. Article text is
untrusted input, not authority to change code or place orders.

## Affordable data stack — verified public documentation September 6

| Need | Candidate | Cost/qualification |
|---|---|---|
| Consolidated historical stock bars/quotes | Alpaca SIP historical | Existing access downloaded this cache. Basic excludes the latest 15 minutes. |
| Live prices | Alpaca IEX / SIP | Basic $0 covers only IEX live; Algo Trader Plus $99/month covers all US exchanges. Check actual account entitlement. |
| Financial news | Alpaca/Benzinga | Existing historical metadata access observed; full content and real-time access still require an entitlement/coverage check. One provider, not the whole internet. |
| Revenue, debt, cash flow, reported earnings | SEC EDGAR APIs / EdgarTools | Public data free. EdgarTools is an access/parsing library, not a source of analyst consensus. |
| P/E and recommendation trends | Finnhub basic-financials/recommendation endpoints | Candidate free/basic endpoints; exact LITE coverage, historical depth and account access unverified. No paid signup recommended now. |
| Vendor-scored news sentiment | Alpha Vantage NEWS_SENTIMENT | Free key: most datasets up to 25 calls/day; confirm this endpoint's current entitlement. Too limited for broad continuous polling. |
| Packaged historical fundamentals | Financial Modeling Prep | Basic is limited. Starter advertises $22/month **billed annually**, annual fundamentals/ratios/news. Detailed analyst and point-in-time coverage must be checked separately. |

P/E is not an intraday trigger by default. Historical P/E must use earnings that
were public then, not today's revised earnings backfilled into January. Forward
P/E also needs contemporaneous analyst estimates. Analyst ratings/targets are
opinions, not guaranteed future prices. Prioritize dated changes over present-day
consensus when testing historical reactions.

Sources:

- [Alpaca subscription comparison](https://docs.alpaca.markets/us/docs/about-market-data-api)
- [Alpaca feed/entitlement FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
- [Alpaca news history](https://docs.alpaca.markets/us/docs/historical-news-data)
- [News content request](https://docs.alpaca.markets/us/reference/news-3)
- [News streaming schema](https://docs.alpaca.markets/us/docs/streaming-real-time-news)
- [SEC public APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC free access/reuse](https://www.sec.gov/about/webmaster-frequently-asked-questions)
- [Finnhub endpoint descriptions](https://finnhub.io/docs/api/quote)
- [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)
- [Alpha Vantage free limits](https://www.alphavantage.co/support/)
- [FMP prices and limitations](https://site.financialmodelingprep.com/developer/docs/pricing)

## Hosting recommendation, not a deployment

**Budget pick: DigitalOcean Basic regular CPU, 1 GiB / 1 vCPU / 25 GiB, $6/month**,
with included IPv4. Weekly percentage-based backup adds $1.20/month: $7.20 before
tax/overages. This is an estimated starting fit for a bounded watchlist (e.g. 5–20
symbols), bar storage, selected quote windows and filtered news. Memory/disk usage
must be measured before relying on it unattended. Not a full-market tick archive,
local large-language-model host, or heavy concurrent research machine.

- A $4 DigitalOcean 512 MiB plan exists; it is cheaper but provides less buffer.
- AWS Lightsail 1 GiB/40 GB with IPv4 is $7/month before backup/tax. The $3.50 offer
  is 512 MB and IPv6-only, not the equivalent configuration.
- Oracle Always Free is the lowest sticker price, but idle instances may be reclaimed;
  that is an undesirable dependency for an unattended recording task.
- Hetzner remains an option, but June 2026 prices supersede old cheap-plan comparisons;
  CX23 Europe is $6.49/month before IPv4, VAT and backup.

For the chosen DigitalOcean setup:

- Research/delayed-data collection: about $7.20/month including weekly VM backup,
  conditional on existing news/data access, excluding optional sentiment API usage.
- Add live consolidated Alpaca data: about $106.20/month total before those extras.
- The latter is $1,274.40/year, or 25.49% of a $5,000 research allocation. These are
  infrastructure expenses, not losses inside a paper account. Do not assume returns
  cover them. Start with historical/delayed research if minimizing spend.

Use a personal cloud account, personal payment method, MFA, dedicated SSH key and
private-repository read-only deploy key. Do not use Sage cloud/SSO/GitHub credentials.
Do not publish the private repository. Rotate any previously disclosed API secret
before installing it. Keep secrets outside git and do not copy the entire work Mac.

Implementation plan: Ubuntu/Python collector under a non-root service account,
automatic restart and boot startup, clock sync, SQLite/WAL with consistent backups,
bounded retention, provider reconnection/rate-limit handling, and an external
missing-heartbeat alert. A server cannot reliably report its own total outage.
Weekly VM backups alone can lose up to a week's new observations; add daily
consistent data exports with separately costed off-host storage if that loss is
unacceptable. A spending alert is not a hard spend cap. No public dashboard is
needed for the first recorder. Save news around the clock; market data follows
exchange sessions. No brokerage submission module should run on this collector.

Sources:

- [DigitalOcean plans, IPv4 and backup pricing](https://www.digitalocean.com/pricing/droplets)
- [Lightsail bundles](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html)
- [Oracle idle reclamation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Hetzner June 2026 price changes](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)

## Verification and reproduction

From the personal repository root:

```sh
.venv/bin/python -m research.lite_ytd_movement.analyze
.venv/bin/python -m research.lite_ytd_movement.analyze --daily
.venv/bin/python -m unittest research.lite_ytd_movement.test_analyze -v
```

Twelve targeted tests passed, including a separate Decimal parser/recount across
all 170 sessions, exact thresholds, recovery chronology, full-horizon censoring,
missing/reordered bars, unknown sentiment and deterministic repeat results.
These are descriptive-analysis checks, not an additional whole-repository audit.
Existing frozen research and trading application files were not edited. No cloud
resource, API subscription, account reset, broker order, deployment, commit or
push was performed. No credentials were accessed in this turn.
