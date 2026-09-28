# Reverification evidence — 2026-09-14

Candidate release:
`1127c399b1898472f4c9fd9345ac77106287686be9d3d56301873e80f7b29b49`

Measured locally against the immutable release:

- 66 core, adversarial, producer, archive, release, and unit-policy tests passed.
- The release manifest and every allowlisted file hash re-verified.
- A forced live Alpaca read-only run published a complete SPY packet with 302
  joined contracts from 10 requests.
- The isolated consumer accepted the packet and reported all six required data
  sections available with no ingestion error.
- The independent checkpoint recomputed raw-response, archive, packet, and
  consumer-ledger bindings with no issue.
- The two actual credential values were absent from the release, decompressed
  archive, packet, status, run log, and reports.
- All 75 files in the original frozen baseline remained byte-identical.

After explicit destination approval, the same revision was uploaded and
installed on `198.211.113.234`. The server independently reverified the release,
the forced read-only smoke published 302 contracts from 15 bounded responses,
and the path-triggered consumer accepted the exact packet hash into its new
revision-bound ledger. Consumer credential, archive, and IP-socket isolation
passed. The actual credential values were absent from 42 deployed files, the
decompressed archive, and the service journal. After the transient isolation
unit was collected, the final repeat scanned 39 extant files, both decompressed
archives, and the journal with the same result.

The next automatic symbol choice attempted QQQ. Its live IEX bars had a missing
five-minute interval, so the producer recorded `nonconsecutive_bars_QQQ` and
fell back to SPY instead of manufacturing an observation. That packet still
carried 146 sourced QQQ and 156 sourced SPY option contracts. Both provider
archives and both consumer ledger events independently reverified.

A root-level operator checkpoint initially created five unlisted Python bytecode
files because that manual command did not disable bytecode. The timer failed
closed before making a request. Only those five files were removed; the manifest
then reverified. The release was given the filesystem immutable flag, a root
import could no longer change it, and two consecutive timer-triggered runs then
succeeded with zero requests outside the collection window.

The five-session operational checkpoint passed on 2026-09-21. See
[`operational-checkpoint.json`](operational-checkpoint.json) for the sanitized
server audit, which exited successfully with no checkpoint issues.

- All five sessions (September 15, 16, 17, 18, and 21) passed.
- All 1,648 scheduled runs in the audited session windows published packets
  that the consumer accepted: 100% in this observed sample, not a guarantee of
  future reliability. The largest publication gap was 69.076 seconds, below
  the checkpoint's 180-second limit.
- Across the release, 1,695 published archives and 1,695 consumer events
  independently verified; this includes publications outside the narrower
  audited session windows.
- Producer-run latency was 3.198 seconds median, 4.104 seconds at the 95th
  percentile, and 6.308 seconds maximum. These are collection-run durations,
  not market-data age or trading execution latency.
- The approved manifest, revision-bound service paths, active timer/path, and
  consumer network/credential/archive isolation reverified.
- The original frozen service had repeated 20-second timeouts in the morning.
  The later check found 142 successful runs and no timeouts since 19:00 UTC;
  its most recent report was generated at 20:22:51 UTC. No service was restarted
  or changed, and the timeout root cause remains unestablished. Its pre-existing
  missing normalized input still blocks the original OPRA experiment.

The first SSH connection did not deliver its checkpoint result after the
remote process ended. A fresh read-only audit with SSH keepalives returned the
complete passing JSON. This completion closes only the five-session plumbing
checkpoint. The operational goal is marked complete, and the completed
checkpoint automation was deleted from the app. Server collection remains
enabled; deleting the verifier does not stop the server services.

All evidence is plumbing-only. It does not validate profit, execution, fill
quality, or agent efficacy.
