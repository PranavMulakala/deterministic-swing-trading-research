# Indicative shadow deployment checklist

## Scope and release

- [x] Separate experiment ID, config, protocol, and ledger kind
- [x] Plumbing-only and non-execution labels in JSON and HTML reports
- [x] Producer source contains only allowlisted HTTPS GET capability
- [x] Release manifest contains no credential and rejects unlisted files
- [x] Revision-bound consumer state preserves engine/ledger identity on upgrade
- [x] Previous release and state remain available through `rollback.sh`

## Local gates

- [x] Core, adversarial, producer, archive, release, and deployment unit tests pass
- [x] Full packet is validated and hashed before indicative ledger compaction
- [x] Exact provider bytes, size, and SHA-256 are retained in compressed archives
- [x] Pagination loops, response/request bounds, stale data, and foreign sources fail closed
- [x] SPY/QQQ fallback handles a preferred symbol with nonconsecutive bars

## Server gates

- [ ] Exact final release re-verifies on the server
- [ ] systemd unit verification passes
- [ ] Forced producer smoke publishes a complete packet
- [ ] Path-triggered isolated consumer accepts the same packet hash
- [ ] Consumer cannot read credentials or archives and cannot create an IP socket
- [ ] Active timer records zero network requests outside the collection window
- [ ] Original frozen experiment files and running service remain unchanged
- [ ] Actual secret values are absent from release, packet, archive, logs, and reports

## Operational checkpoint

- [ ] Five complete scheduled regular sessions pass `checkpoint.py`
- [ ] Reliability, latency, request bounds, pagination, archive hashes, and consumer bindings captured
- [ ] Results remain labeled plumbing-only; no P&L or agent comparison is interpreted

Rollback trigger: any credential exposure, mutating broker capability, release
integrity failure, consumer network/credential access, ledger binding failure,
or repeated session gap. Stop the indicative timer/path and activate the prior
immutable release with its `rollback.sh`.

