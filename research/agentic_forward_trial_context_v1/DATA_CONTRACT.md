# Data contract and current blockers

The decision layer accepts only caller-supplied `ArchiveReceipt` objects that
have already been created from a provider archive. It has no fetch API, URL,
credential field, or fallback value. All fields are point-in-time facts or the
result is `BLOCKED_DATA`.

| Arm | Required evidence | Current blocker |
| --- | --- | --- |
| price stock | fresh quote/technical packet, 50-day basis, earnings distance | 1,200s collection delay; 20-session warmup; no earnings source |
| context stock | all price-stock inputs plus market, raw news, macro coverage | same stock gaps plus no validated context-receipt export path |
| price options | fresh complete SPY/QQQ chain and selected contract | no option-chain stream; 30s freshness not met |
| context options | all price-option inputs plus market, raw news, macro coverage | same option gaps plus no validated context-receipt export path |

The context feed is bounded, not comprehensive internet scraping. Sector scope is
the exact 13-symbol prospective cloud mapping for optical names and a documented
subset for SPY/QQQ. Missing mapped pages are unknown. Fundamentals, analyst
ratings, social-media sentiment, and model-generated interpretations are outside
v1.

To unblock a future version, archive a primary-source earnings calendar, at least
50 point-in-time daily sessions, a complete option chain within 30 seconds, and
fresh quote/market inputs. Then add a tested archive exporter and a complete
modeled fill/mark/exit lifecycle. Do not relabel 20-minute-old data as fresh.

