# Next stock-paper goal — September 24, 2026

**Goal:** On the existing Droplet, deliver reliable, position-specific **Alpaca
paper-only** LITE emails for a reviewed paper holding. Emails should prompt the
owner to decide about a profit target, drawdown, new news, and periodic thesis
review. Selling remains manual. This is an operational notification goal, not a
claim that the LITE strategy is profitable and not authority to place an order.

## Completion criteria

1. A real Alpaca **paper** LITE position is visible through GET-only account,
   position, order, and clock reads. A separately authorized paper order or an
   owner-entered paper fill can create it; this document authorizes neither.
2. A private position card matches its paper account, asset, side and quantity.
   The owner has selected its target price, first-seen news cutoff, drawdown
   review thresholds, and holding-review interval. There is no automatic stop,
   automatic time exit, or implied sale from a missed email.
3. The deployed worker is drilled against that matched paper position using
   a fresh IEX quote and bounded news. A target or drawdown test is an **email
   prompt**, never an order; mismatches and stale data produce clear warnings.
4. The owner receives a labeled position-alert drill in the selected inbox.
   A repeated event produces no duplicate; a failed provider send remains
   visible for retry before expiry. A missed run or whole-host outage has an
   independent detection path.
5. Only after the above, a documented market-window cadence is enabled and
   observed across an actual open and close. The timer is for alerts, not
   broker orders. No arbitrary number of paper days is a completion criterion.

## Measured state at this checkpoint

- September 24: one labeled delivery test reached the configured inbox at
  10:26 a.m. Eastern; replay of the same test ID was suppressed.
- September 24: Alpaca paper GET found an ACTIVE account with zero positions
  and zero open orders. An IEX LITE quote was current at the check instant and
  the first LITE news page was accessible. An unprivileged no-send worker run
  returned `no_paper_position`.
- September 24: 55 focused offline tests passed earlier; three targeted fake
  position/mismatch/delivery-failure tests passed again while preparing this
  goal. Fake fills and messages establish code behavior, not market edge.
- The stock service is installed as a static one-shot unit. There is no stock
  timer, approved position card, or broker order method. The existing IBKR MNQ
  and Robinhood work are separate.
- Later on September 24, the public source IP no longer matched the exact
  DigitalOcean SSH allowlist. Two pinned SSH attempts timed out. A deployed
  server-side synthetic drill was therefore **not refreshed**. Local fake tests
  passed; previously recorded deployed-worker hash and live checks remain
  dated evidence, not proof of current server health. The signed-in Chrome
  browser surface was unavailable for an independent dashboard refresh.

## Immediate gate

At the September 24 checkpoint, the missing paper position and owner-chosen
card values prevented position-specific activation, and the changed source IP
prevented remote verification. The September 25 verification below resolves
the access and installed-code checks. The paper position and reviewed card
remain the activation gate. Do not translate the user's earlier example price
zones or the historical ten-session assumption into default rules.

Source: [activation gate](STOCK_PAPER_ACTIVATION_GATE_20260923.md),
[alert plan](STOCK_PAPER_ALERT_PLAN_20260923.md),
[current worker tests](../research/alpaca_stock_paper_v1/test_worker.py), and
[original handoff](PROJECT_HANDOFF_20260922.md).

## September 25 verification (about 9:11–9:13 a.m. Eastern)

- The current home public IPv4 matched the previously approved exact `/32`
  SSH firewall rule. Pinned, key-based SSH reached the existing Droplet; no
  firewall rule was changed.
- All deployed stock-paper Python source files and both installed one-shot
  systemd unit files matched their local SHA-256 hashes. The units remained
  `static` and `inactive`; no stock-paper timer appeared in the server timer
  inventory. Server-side `systemd-analyze verify` passed, and the private
  configuration retained root ownership and mode `0600`.
- The focused local stock-paper suite passed **55 tests**. A copied, fake-only
  worker test file ran against the installed server code and passed **10 tests**;
  its temporary copy was removed. These counts concern this component, not
  the older project-wide inventory or a trading strategy backtest.
- A GET-only Alpaca paper refresh reported an active paper read, **zero
  positions**, **zero open orders**, and a closed market clock. An isolated
  no-send worker invocation returned `no_paper_position`, zero drafts, and
  zero provider submissions.
- The LITE IEX/news endpoints responded. At this pre-open instant the quote
  was about **61,939 seconds old**, so this check does not establish an
  executable or timely price alert during today's regular session. The first
  news page held 50 items and indicated more pages. No price, headline,
  credential, account ID, or email address was displayed.

**Result:** The deployed notification code and account connection are
established for the no-position case. Position-specific alert delivery remains
unverified because there is no paper holding or owner-reviewed card. The
service remains unscheduled; no paper order, automatic sale, real-money action,
new email, or trading-rule change was made. The next meaningful gate is a
separately authorized paper LITE holding and its reviewed card, followed by
the position-alert and delivery drill in the completion criteria above.
