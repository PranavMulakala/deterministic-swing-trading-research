# Paper Readiness Review

## Verdict

**NO-GO for a faithful v1 Alpaca paper trial.**

The software path is implemented and fake-broker tested end to end, but three broker/experiment mismatches prevent an honest claim that this is v1 unchanged:

1. Alpaca documents fractional equity orders as DAY-only. DAY stops expire at the close, so they are not persistent protection for an overnight swing. The adapter therefore permits only whole-share GTC OTO entries.
2. The frozen backtest enters at the next daily open. The human approval flow submits during the regular session after a fresh quote, so the actual fill is not guaranteed to be the opening print.
3. The paper scanner uses Alpaca IEX `adjustment=all` bars, while the frozen experiment uses pinned Yahoo total-return-style adjusted OHLC. Vendor, feed, and corporate-action differences mean live signal fidelity has not been established.

Alpaca also documents paper-environment simplifications that affect interpretation: Paper Only accounts receive IEX data, paper accounts do not simulate dividends, and eligible orders receive a random partial fill 10% of the time. An OTO exit leg does not become active until the entry is completely filled, so this application treats any observed partial entry as an unprotected-position discrepancy and latches the kill switch. These are test-environment behaviors, not evidence about live execution quality.

The independently validated v1 already underperformed both benchmarks out of sample. This adapter is useful for testing operational correctness, not evidence that the strategy has acquired an edge.

The older versioned paper guide described pattern-day-trader checks. The current paper guide no longer lists that behavior, and Alpaca’s [July 6, 2026 changelog](https://docs.alpaca.markets/us/changelog/2026-07-06-pdt-db49dba) removes PDT fields and configurations from Trading API account schemas. This project makes no claim that those legacy checks remain active; current owner-account restrictions remain unverified.

## Post-hoc whole-share diagnostic

To quantify the Alpaca constraint without altering frozen v1, the same pinned data, dates, signals, costs, and risk limits were replayed with fractional precision set to zero. This is an execution-feasibility diagnostic created after seeing v1 results, not a preregistered strategy result:

- out-of-sample ending equity: **$587.29** from $500 (**17.46%** total return);
- out-of-sample trades: **395**;
- zero-quantity rejections: **713 of 1,108 entry attempts (64.35%)**;
- out-of-sample maximum drawdown: **3.82%**;
- unchanged frozen-period benchmarks: SPY **$1,099.85** and momentum **$793.05**.

Reproduce the diagnostic without writing artifacts:

```bash
PYTHONPATH=src python3 -m swingbot.cli analyze-paper-constraint --root .
```

## Measured software scope

The independent audit of `35b570c` inspected all 26 source modules and 19 test/support modules and reproduced 132 passing tests, but found five major and two minor remaining defects. The subsequent owner-authorized fixes add a twentieth test/support module with adversarial regression coverage. A separate follow-up review reproduced the initial 149-test result, found one later-reconciliation gap in contradictory child-stop fill handling, and added its regression. The resulting implementation has 150 passing tests, including 18 tests in the new re-audit module. These are not fresh certification of the eventual exact commit, mathematical correctness, or 100% line/branch coverage.

The automated suite exercises:

- exact rejection of Alpaca's live endpoint and any alternate trading endpoint;
- every Alpaca adapter read endpoint, exact query construction, nested-order parsing, multi-page historical bars, transport success/error handling, and every adapter safety-rejection branch;
- every documented paper CLI command, monitor interval validation and output deduplication, and fail-closed exit checks without broker network calls;
- exact market/GTC/OTO entry payload and broker-native stop payload;
- secret redaction from adapter exceptions;
- structural absence of LLM imports from all decision/execution modules and network isolation to the two approved adapters;
- frozen strategy-config binding and rejection of weakened paper settings;
- $100,000 default paper balance rejection, clean $500 account binding, long/cash-only checks;
- stale, excessively future-dated, malformed, wide-spread, and materially changed quote rejection, with a fixed two-second tolerance for a quote sampled just after the broker clock;
- final pre-mutation account/order/position/quote refresh with the broker clock sampled last, plus a journal-bound adapter deadline at the earliest proposal, quote-age, or regular-session boundary; JSON preparation precedes the permit claim, and the production HTTPS connection rechecks after TLS setup and before each header/body write using a conservative broker/monotonic clock with a two-second reserve;
- post-acknowledgement broker-clock validation for fill timestamps, including a normal fill that occurs after preflight;
- finite, positive, internally consistent daily OHLCV validation before indicator or signal creation;
- whole-share cash/risk sizing and the 0.5% per-trade limit;
- 3% aggregate open risk including submitted-but-not-filled entries; a market-driven ratio overrun warns and blocks additional entry risk without deadlocking approved exits;
- daily loss halt based on the first durable equity observation of the trading day rather than Alpaca's previous-close `last_equity`, duplicate client ID defense, and kill switches;
- current-session daily bar exclusion (no incomplete-bar look-ahead);
- a timestamped non-authoritative failure record for every rejected or failed public paper operation, without masking the original error;
- append-only hash-chain tamper detection, cross-checked authorization tables, generic-append rejection for authorization and authoritative state events, and one-use, expiring approval bound to the exact latest review;
- cross-process serialization of every public workflow operation, including broker snapshots, reconciliation, proposal/review changes, approval, stop cancellation, and submission;
- unknown, duplicate, malformed, status-regressing, or quantity-regressing broker state; account mismatch; partial fills; and inactive, missing, malformed, or orphan native stops;
- broker-fill-driven local position creation/removal using broker fill timestamps, fill-ledger cash reconciliation, account/position market-value identities, and point-in-time account/cash/mark/P&L snapshots;
- chronological and idempotent recovery when a complete entry and protective-stop fill both occur between polls, plus broker-versus-ledger average-entry-price comparison at the declared one-cent tolerance;
- exact stop-id/price-bound cancellation confirmation before an approved ordinary exit, bounded polling for Alpaca's asynchronous cancellation, rejection of partial-fill evidence, post-cancel account/clock/position revalidation, and independent adapter plus durable-journal submission gates;
- malformed broker read/parsing failures latch durably before propagation; immediate acknowledgements and later reconciliation reject contradictory working entry, exit, and child-order fill evidence;
- atomic SQLite snapshot publication through pinned directory descriptors, with concurrent writer, directory/leaf replacement, failed publication, and legacy WAL compatibility regressions;
- explicit disabling of environment HTTP proxies for broker egress, bounded historical-bar and full order-history pagination, owner-only permissions for the journal/dashboard, and leaf/ancestor symbolic-link rejection on sensitive local paths;
- restart recovery of one exact broker order by client order ID, with a latched kill switch and no retry when zero or multiple matches remain unresolved;
- an explicitly confirmed clean-$500 rebaseline after manual broker recovery that preserves the old audit trail, resets operational state, restarts the paper gate, and invalidates every prior-run proposal and permit;
- unchanged frozen v1 deterministic backtest tests and artifact reproduction.

Most tests use an injected fake broker. A separate test exercises the production urllib HTTPS handler with a fake socket, including expiration during connection setup and between header and body writes. No real broker socket is opened. A local deadline check cannot guarantee broker arrival time or exclude arbitrary OS suspension after a check; an uncertain transmission stays one-use and latches rather than retrying.

The suite uses no real broker account. It does not prove Alpaca accepted a real request from the owner's account. The journal hash chain detects mutation, reordering, and gaps inside an existing database; it is not a signed external audit anchor and cannot prove that an attacker did not delete or fully rebuild the database. The approval controls protect the supplied application path from accidental or unauthorized-in-workflow submission; Python is not a security sandbox against a hostile local user who can read source and credentials or write a separate broker client.

## Unverified external state

- No paper credentials were read or stored during development.
- The owner's paper account ID, status, current balance, permissions, asset flags, and market-data entitlement are unverified.
- No paper order was submitted.
- No real Alpaca fill, child stop, cancel, restart, or reconciliation cycle was observed.
- The resulting fixes still require a fresh read-only audit from their exact commit. The read-only audit of `35b570c` found five major and two minor remaining defects; `PAPER_AUDIT_RESPONSE.md` records their subsequent implementation, the follow-up R8 finding, and verification. Earlier reports do not certify the changed tree.

## Decision required before an operational trial

Choose and pre-register one of these materially different paths:

- keep Alpaca and accept whole-share-only sizing, then rerun the historical test under the same constraint and define a near-open approval window;
- raise the paper allocation enough that whole-share sizing can satisfy the 0.5% risk limit more often, then rerun and re-register the experiment;
- select a broker whose current official documentation and paper environment support fractional entries plus persistent broker-native protective stops, then implement and validate that adapter.

Until that choice is made, keep `SWINGBOT_KILL_SWITCH=1` and do not execute a paper order.

## Primary broker references

- [Alpaca create-order reference](https://docs.alpaca.markets/us/reference/postorder)
- [Alpaca order types, time-in-force matrix, advanced orders, and lifecycle](https://docs.alpaca.markets/us/docs/orders-at-alpaca)
- [Alpaca list-orders pagination and nested retrieval](https://docs.alpaca.markets/us/reference/getallorders-1)
- [Alpaca Broker API trading examples and order fields](https://docs.alpaca.markets/us/docs/brokerapi-trading)
- [Alpaca account endpoint](https://docs.alpaca.markets/us/reference/getaccount-1)
- [Alpaca asset endpoint](https://docs.alpaca.markets/us/reference/get-v2-assets-symbol_or_asset_id)
- [Alpaca latest quote endpoint](https://docs.alpaca.markets/us/reference/stocklatestquotesingle-1)
- [Alpaca historical bars endpoint](https://docs.alpaca.markets/us/v1.4.2/reference/stockbars)
- [Alpaca paper-trading behavior and limitations](https://docs.alpaca.markets/us/docs/paper-trading)
- [Alpaca market clock endpoint](https://docs.alpaca.markets/us/reference/legacyclock)
- [Alpaca market calendar endpoint](https://docs.alpaca.markets/us/reference/legacycalendar)
