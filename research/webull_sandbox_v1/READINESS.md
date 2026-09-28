# Webull MNQ paper readiness — September 10, 2026

**NOT READY for MNQ automated paper execution or live trading.**
Authentication and account/contract discovery work. The tested sandbox quote
endpoints reject MNQU6 and explicitly say that only `MESmain` is supported.
This is an observed symbol restriction, not evidence that buying a subscription
will fix it. No further purchase is justified from these results.

## Measured account and contract checks

Checks at 00:22 Pacific, confirmed again at 00:25 Pacific on September 10:

| Check | Result |
|---|---|
| Saved Webull credentials | Accepted by `api.sandbox.webull.com`; five sandbox accounts returned. |
| Futures account | Exactly one returned account has `account_class=FUTURES`. `account_type=MARGIN` is a separate field. |
| Futures balance read | HTTP 200; does not establish order permission or the proposed $5,000 research balance. |
| Futures positions | HTTP 200, empty list at observation time. |
| Futures working orders | HTTP 200, empty data list at observation time. |
| MNQU6 contract | HTTP 200, September 2026 monthly contract, `OC` status, `XCME`, USD. |
| Contract arithmetic | Multiplier 2 dollars per index point, minimum tick 0.25, so 0.50 dollars per tick. Last trading date 2026-09-18. |
| MNQU6 snapshot | HTTP 417, `ILLEGAL_PARAMETER`, message `only these symbols are supported:[mesmain]`. |
| MNQU6 depth | Same HTTP 417 and symbol-restriction message. |
| Orders submitted by this work | **Zero.** All order-writing requests are blocked by the probe. |
| Actual paper/simulation round trips | None collected. No win-rate or execution-quality estimate follows from this check. |

Scope: the errors came from this account's sandbox snapshot and depth endpoints
for `MNQU6`. They do not prove all Webull environments reject MNQ, nor that MNQ
orders would be rejected. Order submission remains untested. `MESmain` is a
different product and a continuous alias; substituting it would not validate
our frozen MNQ strategy.

## What is implemented

- `probe.py`: repeatable account, balance, position, working-order, contract,
  snapshot and depth reads, with sanitized dated receipts. Only the sandbox
  host, exact approved GET paths/parameters and MNQU6 are permitted. TLS
  verification is required; redirects, request bodies and order writes are
  blocked. Each run permits at most 16 HTTP attempts and no automatic retries.
- Credential loading accepts the user's existing `PAPER_TRADING_APP_KEY` and
  `PAPER_TRADING_APP_SECRET`; the earlier `API` spelling also works. The real
  `.env` is unchanged and ignored by Git. SDK debug logging is disabled.
- Actual probe receipts are in the ignored `outputs/paper/webull_sandbox/`
  directory; `latest.json` points to a dated receipt. These are access evidence,
  **not** normalized broker fill exports. Response hashes establish the response
  identity, not an independently verifiable retained raw response.
- The existing offline comparator is exercised separately with missing actual
  broker and forward-simulation records. It must report `EVIDENCE_BLOCKED`.
  We do not turn account snapshots or fixture trades into a broker receipt.

**50 focused tests passed:** 11 Webull boundary/evidence tests and 39 existing
comparator tests. All five frozen research files match the previous validation
hashes. The independent code review's failed-check exit-status and stale-request
attribution findings were fixed and regression-tested; malformed JSON with an
HTTP 200 is also treated as unavailable evidence.

Review the sanitized [access receipt](ACCESS_EVIDENCE_20260910.json),
[comparison verdict](COMPARISON_STATUS.json), and
[validation record](VALIDATION.json). The software tests use fixtures; the API
receipt separately records actual read-only sandbox observations.

## Upcoming session and next action

A task follow-up is scheduled for **06:15 Pacific, September 10**, before the
06:30 U.S. cash open. It should run one bounded read-only refresh, report changes
or the same exact blocker, and pause itself after the morning handoff. It must
not start an order loop. There is no continuously running Webull market collector.

The next useful external action is to establish a supported MNQ quote/replay
route and whether this sandbox can actually simulate the monthly MNQ contract.
The drafted support question in `SUPPORT_QUESTION.md` is ready for the owner;
it has **not** been sent. Do not fund an account or buy data on the assumption
that it removes the observed restriction.

After a supported feed exists, remaining work includes complete timestamped
MNQ market recording, unchanged-rule forward replay, real broker fees/margin,
bounded sandbox order tests, protective-order and disconnect/restart recovery,
and matching actual paper receipts to simulator receipts. No order adapter or
unattended execution loop is armed. The former 24-session, zero-setup research
result remains unchanged; this connectivity work establishes no trading edge.

Webull documents individual futures stop orders but no futures OCO/OTO/OTOCO
brackets. Also, a native last-trade stop or limit profit target must not be
declared equivalent to the frozen simulator's delayed BBO-triggered market exit.
That design and recovery behavior must be tested before order automation.

## Repeat and interpret the checks

From the project root, use the already installed isolated runtime:

```sh
outputs/tmp/webull-check-venv/bin/python research/webull_sandbox_v1/probe.py
outputs/tmp/webull-check-venv/bin/python -m unittest research.webull_sandbox_v1.test_probe
```

Exit 0 means required read endpoints responded, **not execution readiness**.
Exit 2 means access checks are unavailable; exit 1 means setup failed or the
probe was interrupted. `execution_readiness` always remains `NOT_READY` in this
read-only tool. A stale saved receipt must not be presented as a current check.
Network-restricted runs may fail DNS and need the existing network approval
mechanism. Do not edit host names or disable TLS to work around a failure.

For actual later paired evidence, use the existing
[`mnq_paper_validation_v1` import contract](../mnq_paper_validation_v1/README.md).
It requires actual orders/fills, complete cash and fee records, the same contract
and market stream, and clock/strategy provenance. It cannot be populated honestly
from today's account-discovery results.

## Official references checked September 10

- [SDK and sandbox hosts](https://developer.webull.com/apis/docs/sdk/)
- [Account fields](https://developer.webull.com/apis/docs/reference/account-list/)
- [Futures contract fields and statuses](https://developer.webull.com/apis/docs/reference/futures-instrument-list/)
- [Snapshot fields and timestamps](https://developer.webull.com/apis/docs/reference/futures-snapshot/)
- [Futures order restrictions](https://developer.webull.com/apis/docs/trade-api/futures/)
- [Market-data permissions and sandbox delays](https://developer.webull.com/apis/docs/market-data-api/overview/)

The snapshot's `quote_time` and `last_trade_time` have different meanings.
A recently generated snapshot alone does not prove its underlying prices are
real-time. The general documentation describes delayed sandbox data and separate
OpenAPI entitlements; the specific MNQ symbol rejection above is the measured
result for this setup.
