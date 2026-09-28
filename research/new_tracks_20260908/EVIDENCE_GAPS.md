# Research evidence and remaining gaps

As of September 8, 2026. Research deliverable complete; new trading tracks remain drafts.

| Claim family | Evidence inspected | Confidence and limits | Remaining decision or test |
| --- | --- | --- | --- |
| Futures setup | User's complete ShamanJohnny excerpt; CME contract specifications; NinjaTrader delta and TradingView delta documentation | High confidence about missing strategy definitions and data-method difference; no verified trading edge | Choose instrument/capital, formalize exact rules, obtain matching data, preregister and test |
| SPY wheel mechanics | OIC cash-secured-put and covered-call guides; Alpaca options documentation | Established mechanics; wheel interpretation is inferred from incomplete Reddit account | Collateral, strike rule, below-cost calls, assignment and loss policy |
| Premium arithmetic | Recomputed $905 x 52 / $600,000; illustrative one-contract expiration example | Arithmetic verified; poster returns and account not authenticated | Total return including option liabilities, dividends, costs and marked stock losses |
| Platform support | Official IBKR/QuantConnect, NinjaTrader, Sierra, TradingView, Alpaca and Tradier documentation | Documented capabilities; no account entitlement, all-in price or live execution certification | Paper account eligibility, exact data package and fill/assignment tests |
| Alpaca paper fidelity | Paper documentation explicitly omits dividends and several execution costs; paper assignment activity delay documented | High confidence in documented limitations | Independent ledger and reconciliation; OPRA rather than indicative fill validation |
| GitHub suitability | Jackrabbit docs/configuration; Zero Sum scheduler; Robinhood order handler and security notes | Selected-source inspection only, not full audit; some Jackrabbit execution files unavailable | No repository adopted, installed or given account access |
| Official Robinhood AI tools | Official Agentic overview and Trading with your agent pages | Current documented support exists; distinct from third-party repo | Paper mode not established; eligibility and lifecycle not tested |
| Hosting | Deployment manifest, boot-enabled service, live 20-symbol snapshots, namespace accessibility/read-only probes and loopback listener | Runtime properties verified at deployment; not a reliability or reboot certification | Private SSH viewing requires connection; no public sign-in site deployed |
| PDF | Seven rendered pages visually reviewed; 25 HTTPS link annotations and extracted text checked | Layout/readability and embedded links verified; not a fresh remote link availability check | None for report delivery |

Source URLs and claim citations appear alongside the corresponding statements in DECISION_GUIDE.md and its PDF. Research stopped after the major decision gaps were reconciled; a paid-indicator performance ranking is unsupported and was not fabricated. No model or platform was empirically shown to produce the safest, fastest or highest-profit strategy.

The two required owner choices remain realistic simulated capital for each track and futures versus an explicitly separate ETF version for track A. No expiry, risk, entry or sizing proposal in the guide is an approved frozen rule or an authorization to place orders.
