# Draft support question — not sent

We are integrating an individual OpenAPI sandbox account for personal MNQ
futures paper research using the official Python SDK 3.0.0 and
`api.sandbox.webull.com`.

On September 10, 2026 at approximately 07:22 UTC:

- Account listing returned a FUTURES account; balances, positions and open-order
  reads succeeded.
- `/trading/instruments/futures/contracts/list` returned `MNQU6` as an `OC`
  monthly contract.
- `/market-data/futures/snapshots/list` with `symbols=MNQU6&category=US_FUTURES`
  and `/market-data/futures/depths/list` with
  `symbol=MNQU6&category=US_FUTURES&depth=1` both returned HTTP 417,
  `ILLEGAL_PARAMETER`: `only these symbols are supported:[mesmain]`.

Is this the intended sandbox symbol limitation? Is there a supported way to
obtain MNQ quotes and simulate orders for an explicit monthly MNQ contract via
OpenAPI, without placing live orders? If access changes are required, please
identify the exact sandbox/account setting, eligibility requirements, data
delay/model and any cost before we subscribe. Does any production OpenAPI data
entitlement expand this particular sandbox symbol whitelist?

We have submitted no orders. Please do not include API keys or secrets in any
reply or ticket. Account-identifying details can be provided privately through
the authenticated support channel if required.
