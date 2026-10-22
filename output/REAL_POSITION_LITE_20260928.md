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

## Oct 12, 2026: owner's add during the optics selloff

From the owner's Robinhood screenshot at 11:35 ET (LITE $1,000.59):

| Field | Value |
| --- | --- |
| Shares | **85.424217** (was 51.013957) |
| Average cost | **$1,055.91** (was $1,078.14) |
| Cost | about **$90,200** (was $55,000) |
| Added today | about 34.41 sh for about $35,200, average about $1,022.95 (one or more buys from ~9:40 ET; the owner first said $10–15k) |
| Market value | $85,474.62 |
| Today's return | −$6,011.89 (−6.57%) |
| Total return | −$4,725.38 (−5.24%) |
| Robinhood "portfolio diversity" | 62.88% |

Context: optical stocks fell together (CIEN −9.5%, AAOI −8.2%, COHR −7.7% at 11:32) while SPY was flat; "sell the news" around the OCP Global Summit, memory selloff from Asia, TSMC earnings Thursday. LITE's 16th day of 2026 with a 10%+ intraday drop.

Reference levels from the new average ($1,055.91, 85.42 sh):

| Level | Price | Gain / loss |
| --- | ---: | ---: |
| +3% | $1,087.59 | +$2,706 |
| +2% | $1,077.03 | +$1,804 |
| Break-even | $1,055.91 | $0 |
| −10% | $950.32 | −$9,020 |
| −20% limit | $844.73 | −$18,040 |
| −30% | $739.14 | −$27,060 |
| −43% (May–July 2026 drop) | $601.87 | −$38,790 |

Combined with MU (50.96 sh @ $1,079.08): about $145,200 at cost; the combined −20% line is about −$29,000.

### Oct 12, 3:55 PM ET: second add

Robinhood screenshot (LITE $994.96): **105.607684 sh @ $1,043.48** (about **$110,200** cost); market value $105,075.42; today −$6,411.08; total −$5,124.58; portfolio diversity 67.75%. This add was about 20.18 sh for about $20,000 (about $990.87). Total added on Oct 12: about 54.6 sh for about $55,200. LITE closed about $995.10 (−9.8%, IEX).

| Level | Price | Gain / loss |
| --- | ---: | ---: |
| $1,150 | $1,150.00 | +$11,249 |
| Break-even | $1,043.48 | $0 |
| −10% | $939.13 | −$11,020 |
| −20% limit | $834.78 | −$22,040 |
| −30% | $730.44 | −$33,060 |

Combined with MU: about $165,200 at cost; combined −20% is about −$33,000. Crowd reactions for the day: `outputs/chatter/dip_reactions_20261012_raw.json`.

### Oct 14, 2026: owner's $20,000 add at $904.90

Owner-reported (not yet confirmed by screenshot): bought $20,000 of LITE at $904.90, about 22.1019 sh. New position about **127.7096 sh @ $1,019.50** (about $130,200 cost). Each $10 LITE move = about $1,277. Cash left about $2.2k of the ~$22.2k buying power; the ~$16k 2026 tax set-aside (Oct 4) and the HOOD gain's tax should be checked.
Confirmed by Robinhood screenshot, 3:35 PM ET (LITE $903.93): **127.708357 sh @ $1,019.51**; market value $115,438.78; today −$8,900.56 (−7.16%); total −$14,761.22 (−11.34%); portfolio diversity 70.99%.

Oct 14 close (IEX last trade): LITE $896.58 (−9.23%). Position 127.708357 sh @ $1,019.51: −$15,698 (−12.1%); today about −$9,817. MU close $914.20: 50.97 sh @ $1,079.08, −$8,404 (−15.3%).

### Oct 22, 2026 ~2:08 PM ET: optics selloff resumes
IEX last: LITE $751.82 (−11.7% today; −34% from the $1,143 Oct 9 high), MU $861.97 (−5.7%). LITE 127.708357 sh @ $1,019.51: about −$34,190 (−26.3%), today about −$12,690. MU 50.97 @ $1,079.08: about −$11,070 (−20.1%). Combined about −$45,260 on ~$185,200 cost; the owner's −20% line ($815.61) was crossed today. Peers: COHR −13.7%, AAOI −13.7%, MRVL −9.5%, SMH −5.7%, QQQ −2.9%. No company-specific news found; coverage cites a chip-led tech selloff and pre-earnings caution (LITE reports early Nov).
