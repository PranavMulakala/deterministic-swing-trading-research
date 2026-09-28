# Stock paper setup status — September 23, 2026

This is a read-only setup check for the user's existing infrastructure. It does not
approve a stock strategy, place a paper or real order, install a runner, change a
service, buy data, or authorize a future trade. Earlier frozen research and cloud
services remain separate.

## Accounts and host observed today

- The signed-in Alpaca dashboard was in **Paper Trading** mode at approximately
  10:35 a.m. New York time. It displayed **$7,500 simulated cash**, **$30,000
  paper buying power**, **no open positions**, and **no recent orders**. The paper
  endpoint was displayed. No account number, API key, secret, or credential is
  retained here. The $30,000 figure must never be used as a position budget for
  a cash-only experiment; the program needs an independent one-times-cash cap.
- The signed-in DigitalOcean console showed one `personal-trading-research`
  Droplet, **Active**, in NYC1 with Ubuntu 24.04, **2 GB RAM / 50 GB disk**,
  estimated at **$12/month**. Its overview showed **14.9% CPU** and **42.0%
  memory** usage in the last-hour tile at the time observed. These readings
  establish capacity at that instant, not sustained load headroom or application
  health. Automated backups were not enabled in the Droplets view.
- A second **read-only DigitalOcean overview check around 12:29 p.m. New York
  time** still showed that Droplet **Active**, at the same estimated **$12/month**,
  with the last-hour tile at **33.2% CPU** and **43.2% memory**. This verifies
  only the host dashboard at that time; it does not verify SSH, the stock-alert
  worker, email delivery, or any existing application's process health. The
  Alpaca paper dashboard values above were **not refreshed** in this later check.
- No new server, market-data subscription, broker account, payment, transfer,
  order, or trading schedule was created by this check.

## What the repository already has

- The [September 21 cloud repair](../cloud/DEPLOYMENT_20260921_REPAIR.md)
  describes delayed market-data collection, a dashboard, retrospective replay,
  and an isolated free stock **simulation** runtime. The stock runtime has no
  broker order client. Its latest preserved stock-session count was one qualified
  session and zero closed trades, a dated snapshot rather than today's count.
- [Paper readiness](../PAPER_READINESS.md) concerns the original ETF strategy.
  That adapter's whole-share GTC OTO design, entry timing, and adjusted-data
  semantics are not a validated LITE multiday broker runner.
- [The September 22 handoff](PROJECT_HANDOFF_20260922.md) records the actual
  LITE idea, losing distinct intraday tests, descriptive longer-hold recovery
  evidence, and then-unresolved manual exit/deadline policy. The owner's later
  [September 23 clarification](STOCK_PAPER_ALERT_PLAN_20260923.md) rejects an
  automatic time sale in the proposed paper workflow. The handoff takes precedence over
  any suggestion that the existing paper balance or server implies readiness.

## Smallest useful remaining path

1. Compare opening dip, observable recovery, later entry, simple buy-and-hold,
   and cash on the already available historical data with one funded portfolio
   per case. Preserve all tested variants and adverse outcomes. Treat this as
   already-seen development data, not an unseen profit validation. Original
   decision-time news is unavailable historically, so no news edge can be claimed.
2. Specify manual broken-thesis reviews and notification triggers. The owner
   clarified that a paper position may remain open for months while awaiting its
   target; there is no automatic holding deadline or stop order in the proposed
   workflow. An automated buy combined with manual loss exits requires the
   owner to be reachable for those exits. The comparison's tested deadlines
   remain research assumptions, not approved paper or live policy.
3. Build a separately versioned, paper-only Alpaca adapter after the research
   decision. Bind it to the exact paper account and endpoint; enforce a
   cash-only allocation independent of the broker's $30,000 buying-power
   display. Reconcile orders, fills, positions and pending orders after every
   decision and after restart. Fail closed on missing quotes, uncertain
   submissions, disconnected broker state, or budget mismatch.
4. Verify the exact paper runner with a bounded operational check before any
   unattended schedule is considered. Paper fills cannot establish real-money
   execution quality or future profitability. A later real-money decision
   requires a separate explicit authorization.

The free Alpaca Basic feed can be used for this setup. The optional $99/month
consolidated real-time market-data plan is not needed for the next offline
comparison and has not been purchased.
