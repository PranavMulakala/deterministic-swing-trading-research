# Deployment and operation

These units are namespaced `trading-shadow-indicative-*`; they do not replace,
restart, or modify the original `trading-shadow-7500-*` experiment.

## Install or upgrade

Build a new immutable release with `build.py`, copy the resulting directory to
the server, and verify `RELEASE.json` there. The initial installation is:

```bash
sudo sh /path/to/release/install.sh /path/to/private-dedicated-alpaca.env
```

Later revisions use the already-installed private credential:

```bash
sudo sh /path/to/release/upgrade.sh
```

The installed credential is root-owned mode `0600`. systemd passes it only to
the fixed producer through `LoadCredential`. The DynamicUser consumer receives
no credential, cannot read the raw archive, and has `PrivateNetwork=yes`,
`IPAddressDeny=any`, and `RestrictAddressFamilies=AF_UNIX`.

## Immediate smoke and inspection

The forced smoke makes read-only market-data requests outside the normal
collection window. It never submits an order.

```bash
sudo systemctl start trading-shadow-indicative-smoke.service
sudo systemctl status --no-pager trading-shadow-indicative-smoke.service
sudo systemctl status --no-pager trading-shadow-indicative-consumer.service
sudo systemctl status --no-pager trading-shadow-indicative-producer.timer
sudo systemctl status --no-pager trading-shadow-indicative.path
sudo journalctl -u trading-shadow-indicative-smoke.service -n 20 --no-pager
sudo journalctl -u trading-shadow-indicative-consumer.service -n 20 --no-pager
```

Read the rendered consumer unit to obtain the exact revision-bound state path.
The current report is `report.json` in that directory. A complete accepted
packet reports all six availability flags true and says `INDICATIVE PIPELINE
ONLY`; it must still say `PLUMBING ONLY` and `Real-money options: DISABLED`.

## Five-session checkpoint

After each regular session, run the checkpoint from the active immutable
release. Substitute the exact 64-character revision in both the revision and
ledger path:

```bash
sudo PYTHONPATH=/opt/trading-shadow-indicative-v1-REV/src:/opt/trading-shadow-indicative-v1-REV \
  python3 -m research.agentic_shadow_indicative_v1.checkpoint \
  --run-log /var/lib/trading-shadow-indicative-archive/run-log.jsonl \
  --archive-dir /var/lib/trading-shadow-indicative-archive \
  --ledger /var/lib/private/trading-shadow-indicative-REV/ledger.sqlite \
  --revision REV --required-sessions 5
```

Exit code `2` means the evidence is valid so far but fewer than five complete
sessions passed, or a session is incomplete. Exit code `1` means the audit
inputs themselves are invalid. A pass requires five sessions with continuous
successful publication and consumption from 10:00 through 15:55 Eastern, gaps
of at most three minutes, raw-response and packet hashes that recompute, complete
pagination, bounded request sizes/counts, and no credential-shaped archive keys.
The checkpoint never evaluates simulated returns.

## Rollback

Every installed release includes `rollback.sh`. Run it from the exact older
immutable release you want to reactivate:

```bash
sudo sh /opt/trading-shadow-indicative-v1-OLDER_REV/rollback.sh
```

This verifies the older manifest, renders its units, and reconnects the consumer
to that release's preserved ledger. It does not delete the newer release or
state. After rollback, repeat the forced smoke and status checks above.

## Stop condition

To stop collection without deleting evidence:

```bash
sudo systemctl disable --now trading-shadow-indicative-producer.timer trading-shadow-indicative.path
```

Keep the immutable releases, revision-bound ledgers, run log, and response
archives until the operational checkpoint report is captured.

