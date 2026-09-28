# Real-money position: LITE, opened September 28, 2026

**Separate record.** This is Pranav's own manual purchase in his Robinhood "Individual" account. It is not a paper-bot trade, not part of any research ledger, and not related to Joey's material. Figures come from the owner's Robinhood app screenshot at 10:01 ET. Claude has no Robinhood access in this session and cannot trade.

| Field | Value |
| --- | --- |
| Shares | 33.034698 (fractional) |
| Average cost | $908.14 |
| Cost | $30,000.13 |
| Funding | Cash, no margin (owner-reported) |
| Robinhood "portfolio diversity" | 99.95% LITE. Robinhood counts invested holdings only; cash is probably excluded. |
| Opened | Monday Sep 28, 2026, shortly after the open |
| Exit plan | No automatic stop, per the owner. He will sell at a target price that isn't set yet. He is also considering buying more at $840 or $820. |

## Reference levels

| Level | LITE price | Gain / loss |
| --- | ---: | ---: |
| Today's first IEX trade (≈ the open) | $947.99 | +$1,316 |
| Sep 25 close | $941.64 | +$1,107 |
| +2% | $926.30 | +$600 |
| Break-even | $908.14 | $0 |
| −$500 | $893.00 | −$500 |
| −$1,000 | $877.87 | −$1,000 |
| Owner's $840 level | $840.00 | −$2,251 |
| Owner's $820 level | $820.00 | −$2,912 |
| −43% (the 2026 May→July drop) | $519.46 | −$12,840 |

## If more were bought (arithmetic only; not a recommendation)

| Added | At | Total shares | New average | Each $10 move | Value change at $700 |
| --- | ---: | ---: | ---: | ---: | ---: |
| $10,000 | $840 | 44.94 | $890.09 | $449 | −$8,543 |
| $10,000 | $820 | 45.23 | $884.38 | $452 | −$8,339 |
| $30,000 | $840 | 68.75 | $872.74 | $687 | −$11,876 |
| $30,000 | $820 | 69.62 | $861.82 | $696 | −$11,266 |

## Snapshots (IEX feed)

- 09:58 ET: $903.75
- 10:00 ET: $900.44, the day's low at that time
- 10:01 ET, from Robinhood: $900.92, market value $29,761.62, today −$238.38 (−0.79%)
- 10:03 ET: $908.46, about break-even (+$10.57)

Context at 10:03: SPY was flat (−0.05%), and no new LITE news had appeared since 06:00 (Alpha Vantage). The drop looks LITE-specific: an overnight run-up followed by selling at the open. Peer stocks couldn't be checked because the free data plan hit its limit.

## Price alerts

`research/real_position_alert_v1/` holds a price-only email monitor that cannot trade; its levels are in `position.json`. The delivery test was accepted by Resend at 10:08 ET, and one live check sent nothing. A scheduled background run was installed briefly and **removed by the owner at about 10:10 ET**. Nothing runs the monitor automatically now; it can be run once on request.
