# Covered-call practice log (paper; owner trades, Claude coaches)

- **Account:** Alpaca paper account ending **U036**, created Oct 7, 2026 with $100,000.
  - Keys: `ALPACA_PAPER_API_KEY` / `ALPACA_PAPER_API_SECRET` in `.env`.
  - The old "Swing trading 9-14" account (…CEYJ) was deleted by the owner.
- **Why:** Joey's advice: "try some different trade styles out with a paper account… paper then real money".
- **Goal:** learn the mechanics, the rolling decisions and the dollars before using real money.
- **Report:** dollars only. Each decision gets one line of "why".

## Opening trades: Wed Oct 7, 2026, ~3:34 PM ET (placed by Claude at the owner's request: "place them for me on paper")
| Stock | Shares | Paid | Calls sold | Premium kept | Break-even | Max profit if called away |
|---|---|---|---|---|---|---|
| AMZN (volatility ~39%) | 200 | $259.69 ($51,938) | 2 × Nov 13 $275 @ $6.85 | **$1,370** | $252.84 | **+$4,432** |
| HOOD (volatility ~61%) | 400 | $109.38 ($43,752) | 4 × Nov 13 $120 @ $4.75 | **$1,900** | $104.63 | **+$6,148** |

- **Totals:**
  - $3,270 premium collected;
  - **+$10,580** if both are called away on Nov 13;
  - about −$19,100 if both stocks fall 20%.
- **Cash left:** about $7,580. Rolls should be done for a net credit.
- **Earnings before Nov 13:** both companies report in late October (exact dates not confirmed yet). Decide what to do before each report.

## Starting rules (break them freely, but write down why)
1. Hold to expiration unless one of rules 2–4 applies.
2. **Stock above the strike with ≤ 7 days left:** decide whether to (a) let the shares go for the maximum profit, or (b) roll up and out to next month, only for a net credit.
3. **Call worth ≤ 20% of what we sold it for** (most of the premium is already earned): consider buying it back and selling a new one.
4. **Stock down 15% or more:** review. Options:
   - roll down for more premium, but never to a strike that locks in a loss on the shares without a written reason;
   - hold;
   - exit.
5. **No new calls without the shares to cover them** (never naked).

## Decisions
| Date | Stock | Action | Why | $ effect |
|---|---|---|---|---|
| 2026-10-07 | AMZN, HOOD | Opened (above) | Practice: Joey's range (AMZN) + high volatility (HOOD) | +$3,270 premium |
