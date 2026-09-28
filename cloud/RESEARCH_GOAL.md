# Forward research loop deployment goal

Owner request: build and verify automated paper-only research and evidence-based
improvement review before the September 8, 2026 regular market session. No strategy
rule changes, risk-limit changes, model purchases, or broker orders are authorized.

The app's existing blocked broker-readiness goal cannot be replaced through its
goal tool. This document tracks this separate deployment without falsely marking
that older goal complete.

Acceptance: direct provider five-minute collection; pinned original engines and
20-session warmup; calendar/action checks; delayed-data ORB A/B at both cost/delay
settings and LITE dip/VWAP whole-share replays; persistent results and proposal
memory; no automatic promotion; safe missing-data states; future-data tests;
idempotency; no-network/no-credential runtime fence; automatic server scheduling;
server smoke test and source integrity; operating guide and honest scope limits.

No LLM runs unattended in this version. The research agent is a deterministic
evidence reviewer. It records outcomes and proposes prospective evaluation of
the existing RVOL challenger after 20 sessions and 20 closed trades per arm.
This threshold permits review, not acceptance or proof of edge. The underlying
LLM does not retrain. All rules remain pinned, including ORB $5,000 and LITE $500
research capital; these are separate simulated portfolios.

ETF swing execution remains gated on daily-data parity. LITE uses a separately
labeled SIP/raw input version, not the original IEX/all dataset. New rule edits
would require a separately frozen future evaluation interval before any use.
News metadata is tracked but is not a selection filter or sentiment score.

September 9 prospective additions preserve all September 8 results: separately
labeled `$5,000` and `$10,000` whole-share capital arms reuse the exact LITE entry,
exit, sizing formula, and risk-percentage rules beginning September 9, and a separate `sector_news` stream records
bounded upstream/peer metadata beginning September 9. Neither addition is scored
retroactively, changes selection, authorizes brokerage use, or claims comprehensive
news coverage. Continuous readiness evidence now checks all required streams, data
lag, collector error state, and disk reserve.

Design: collector SQLite -> read-only archive snapshot -> original engines ->
immutable run artifact and ledger audits -> cumulative evidence reviewer ->
SQLite research/proposal memory. The collector alone has market credentials;
the research systemd unit has no network and cannot access the credentials path.
No web ports, broker connection, or LLM API is added.

Deployment acceptance status: implemented; local regression suite and Linux
end-to-end/isolation checks passed. Both timers are enabled. First production
research run correctly reports WAITING_FOR_FIRST_COMPLETED_SESSION. First future
market session and any evidence of improvement remain unobserved. See
RESEARCH_OPERATIONS.md for measured coverage and deliberate exclusions.

Deployment goal accepted at 2026-09-08 07:31 UTC after the first automatic timer
repeat succeeded. This closes the implementation/verification task, not the
older blocked broker-readiness goal or the future question of trading edge.
