# IBKR paper API connection — September 10, 2026

Status: **READ-ONLY CONNECTION VERIFIED; QUOTES AND EXECUTION NOT READY.**

The official Python API SDK 10.50.2 was installed in the isolated environment
`outputs/tmp/ibkr-check-venv`. No API key or `.env` credentials are needed for
this connection to the user's already-authenticated local TWS session.

Two probes ran at 20:47 and 20:48 UTC against `127.0.0.1:7497`.
Both completed the API handshake, matched the exact paper account previously
observed in TWS, and resolved MNQU6: conId 793356225, expiry 2026-09-18,
CME, USD, multiplier 2, minimum tick 0.25. Account identifiers are omitted
from saved reports.

The first 15-second quote observation returned code 10167 and no price.
The second 30-second observation returned market data type 3 (delayed),
but no price callbacks. Therefore delayed mode is confirmed; a working
price stream and real-time entitlement are not confirmed. The absence of
prices during these windows does not establish the cause or prove that a
paid subscription is the only remedy.

Receipts (ignored local files):

- `outputs/paper/ibkr/read_only_probe_20260910.json`
- `outputs/paper/ibkr/read_only_probe_20260910_followup.json`

The probe is `scripts/check_ibkr_paper.py`. Its allowlist blocks order
placement, cancellation, and all other outbound request types except the
specific handshake, account directory, clock, contract and quote requests.
The account gate rejects unknown or mixed account lists before quote requests.
Five offline tests passed, including both protocol paths and account/contract
rejection cases. The request subscriptions were cancelled and the probe
disconnected after observation. No trading process remains running from this check.

Next: establish actual MNQ bid/ask prices and their data type, then prepare
paper execution verification with matched simulation receipts. A delayed
feed cannot validate same-time live execution against real-time simulation
prices. No paper orders or real-money orders were sent; no market-data plan
was purchased. Connection success alone is not evidence of profitability.

Official reference: [IBKR market data types](https://www.interactivebrokers.com/docs/tws-api/doc/market-data-delayed/introduction).

## Follow-up diagnostic, 20:53–20:56 UTC

The issue reproduced with a 30-second streaming check. IBKR returned code
10167: “Requested market data is not subscribed. Displaying delayed market data.”
A separate 20-second delayed-frozen request returned actual type 3, with no
price or trade timestamp. Both checks again verified the account and contract.
TWS reported API server version 226. These are additional observations, not
proof of a specific missing account setting.

The checker now records requested versus returned data type, exchange trade
timestamps when supplied, and bid/ask completeness. It rejects SDK unset-price
sentinels, nonfinite prices and crossed quotes as usable prices. Delayed and
one-sided prices never qualify as a real-time two-sided quote. Seven offline
tests pass. This is still a diagnostic, not an execution readiness gate:
freshness, quote sizes, commissions, margin, order lifecycle and reconciliation
require additional evidence before a runner can be enabled.

Remaining account checks:

1. Inspect **Settings → Market Data Subscriptions → Market Data API
   Acknowledgement**. IBKR requires a reviewed, digitally signed form for API
   data; missing acknowledgement can cause not-subscribed errors. Its actual
   status in this account is not yet known because Client Portal requires login.
2. Inspect actual CME data entitlements and sharing with the paper username.
   Published CME Real-Time L1 nonprofessional pricing is $1.55/month, subject
   to actual classification, account eligibility and the portal's final terms.
   Published individual-account minimum is $500 equity plus subscription cost.
   No funding or subscription has been initiated.
3. Once required settings are confirmed, reconnect and require actual MNQ
   bid/ask callbacks. Preserve delayed/frozen labels. Real-time feed verification
   is required for the planned same-time paper-versus-simulation comparison.

References: [API acknowledgement](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/compliance-requirements-for-api-market-data/market-data-api-acknowledgement),
[data pricing and equity requirements](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php),
[paper data sharing](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/market-data-users/market-data-sharing).

## September 13: account settings inspected directly

The authenticated Client Portal now confirms the API acknowledgement is **not
certified**. The subscription list contains only fee-waived products, no CME
subscription, and no pending subscriptions. Subscriber status is unconfigured
and Non-Commercial status is explicitly not set. The dashboard shows $10 in
cash/equity. These are current account observations, not inferred from error
10167. Paper data sharing has not yet been inspected.

The acknowledgement form is open for the user's review and signature. It is
the Market Data API Supplement to the GFIS Subscriber Agreement, version
4569 dated April 20, 2026. It includes restrictions on third-party data sharing
and systems accessible to third parties, as well as trading-related use tied
to the subscriber's IBKR accounts. The user must review these terms in deciding
whether to accept; we have not signed or submitted it on their behalf.

The checker now prints only diagnostic status, callback counts and error codes;
raw quote values remain in its local receipt. Eight offline tests passed,
including a test that quote values and diagnostic message contents do not
appear in console output. This output change does not establish that any
proposed hosted dashboard or LLM data use is licensed.

TWS was not running when inspected on September 13. After the required account
steps are complete, it must be reopened and logged into paper mode before the
local API check can run. No new quote check, orders, subscriptions or deposits
have been made during this account-settings inspection.

### Acknowledgement completed by the user

Later in the same September 13 session, the portal returned to Market Data
Subscriptions and explicitly confirmed API access **enabled**, with the
acknowledgement signed on September 13. This supersedes the uncertified status
above. The agent observed the result; the user completed the signature.
The next subscriber-status page displayed “Choose One”; it has been opened
for the user's accurate classification. The current CME subscription and
quote-stream blockers are not resolved by the acknowledgement alone.

TWS was subsequently reopened and switched to **Paper Log In**. Credentials
are not entered by the agent; paper authentication is pending the user.
The user also has the subscriber-status dropdown open, still at “Choose One”
when last observed. These two user steps are the immediate dependencies before
further account-specific subscription and API checks. Published CME L1 pricing
and the $500 individual equity minimum were rechecked on September 13; no
purchase or transfer was initiated.

### September 13 follow-up: classification saved and paper connected

The authenticated portal now confirms API acknowledgement enabled and subscriber
status **Non-Professional**. Its subscription catalogue offers **CME Real-Time
(NP,L1) at USD 1.55/month**; this service is not subscribed and none are pending.
Published IBKR requirements were refreshed: individual accounts need USD 500
equity plus the subscription fee. Partial months are charged in full. No new
payment, subscription or transfer was initiated.

Paper Trading Account settings show **No** for sharing real-time subscriptions
with the paper account. This setting is left open for the user; it was not
changed. TWS is now authenticated in Simulated Trading mode.

The bounded read-only probe at 18:46 UTC on September 13 verified the paper
account, API handshake and exact MNQU6 contract. It received zero price callbacks
and error 10167; returned market-data type was unverified. Receipt:
`outputs/paper/ibkr/after_ack_20260913.json`. No order requests were sent.
This Sunday daytime check does not establish how quotes behave during an open
market session. Real-time quote and execution readiness remain unverified.

### September 13 follow-up: questionnaire and sharing completed

The portal confirms the Non-Professional Questionnaire completed September 13.
Reloading Paper Trading Account settings confirms **Yes** for sharing real-time
subscriptions; the user saved this change. The subscription summary still lists
no CME service, USD 0 total and no pending subscriptions after the user's latest
completion message. CME selection in the configuration form is not evidence of
activation. The live dashboard freshly shows USD 10 cash and no positions.
This does not meet the published USD 500 equity plus subscription-fee requirement;
no explicit rejection reason was observed, so funding is an unmet prerequisite,
not a verified explanation of every incomplete subscription step. No additional
probe was run because real-time entitlement remains unverified. The dashboard
and subscription configuration remain open for the user; no transfer or paid
activation was performed by the agent.

## September 21, 2026 — real-time quote check passed

After the user logged out of the competing live session, the bounded read-only probe verified the exact paper account and uniquely resolved CME MNQZ6 (December 18, 2026 expiration). At 16:08:35–16:08:55 UTC, IBKR reported market-data type 1 and delivered 346 price callbacks, including valid non-crossed bid and ask quotes. Receipt: `outputs/paper/ibkr/mnqz6_20260921_after_logout.json`. No orders were sent.

The checker now accepts an explicit December contract selection; the original September selection remains available for reproducibility. Nine offline checks pass, including contract mismatch rejection and order-message blocking. This establishes quote connectivity only: sustained freshness, paper order lifecycle, fill comparison, strategy evidence, and live approval remain separate gates.
