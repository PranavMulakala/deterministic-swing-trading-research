# Third-party research boundaries

No third-party trading repository is imported, vendored or required at runtime.

- **TradingAgents:** influenced the narrow analyst/critic role separation. This package uses original structured-validation code, not its code, memory layer or model orchestration.
- **QuantDinger:** its scoped gateway and idempotent workflow patterns are useful architectural references. No QuantDinger service or dependency is integrated.
- **OpenBB:** a possible future normalized research-data adapter. It does not supply an edge or automatically grant real-time data entitlements.
- **EdgarTools:** a possible future point-in-time SEC filing adapter. It is not presently used, so filings do not drive this version.
- **Fincept:** potentially useful as a human research interface, but a GUI is not needed in this headless deterministic core and is not a dependency.
- **GitHub stock-market topic list:** a discovery directory rather than an auditable runtime component.

Adding one of these tools later requires a separately versioned adapter, license review, timestamp/provenance tests and fail-closed behavior. Marketing claims, screenshots and community returns are not validation evidence.

