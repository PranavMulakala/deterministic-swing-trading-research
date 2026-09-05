# Independent validation record

Validator: Claude Code, running locally and read-only  
Audited commit: `0cf291235e5e75d185ddac3285be6f4ca2bc7a3f`  
Reported: 2026-09-05  
Full report supplied by owner: <https://claude.ai/code/artifact/680b8634-01b9-436d-889e-1c8cacb6ed35>

This file records the owner-supplied audit summary. The validator made no repository changes. The external artifact remains the authority for the validator's complete wording.

## Validator verdict

`VALIDATED`: zero critical or major defects. The validator independently replayed all 1,992 trades, all 514 protective-stop exits, every daily equity row, and the full ledger. It reproduced the OOS values of $680.48 for v1, $1,099.85 for SPY, and $793.05 for momentum, and agreed that v1 should not advance unchanged to broker-paper execution.

## Minor findings and disposition

| Finding | Post-validation disposition |
|---|---|
| Daily 2% halt had zero historical firings and was described as structurally unreachable | Historical zero is now explicit. A backtest integration test proves the open-exit-to-later-entry rejection path; daily-bar intraday ordering limits are documented. No frozen trade logic changed. |
| End-of-window liquidation absent from preregistration/methodology exit list | Added to methodology and the separate post-validation addendum; the original preregistration was not rewritten. |
| Architecture test covered only 6 source modules | Expanded structural scanning to all 14 current `swingbot` Python modules, with fail-closed module-count classification. |
| Total-return adjusted-price semantics undisclosed | Added explicit dividend/split and implicit-reinvestment semantics to methodology. |
| `terminal_flat` validation was tautological | Replaced with an independent replay of every position-open/position-close ledger event. |
| Aggregate-risk validation hardcoded `0.03` | Validation now reads the frozen aggregate limit from the verified config. |

The reported zero-quantity frequency and momentum full-turnover cost drag are now emitted as measured metrics. These changes harden disclosure and validation only; v1's frozen strategy and economic outputs remain the baseline.
