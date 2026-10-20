"""Deploy the EdwardAlerts cloud relay (research/edward_live_v1/cloud.py) to the personal DigitalOcean server.
Paper only: it reads a private ntfy inbox fed by the owner's iPhone Shortcut, places paper copies in ...U036 and sends
Pushover notes. It never touches Discord or a real-money account.

Owner approval: "Yes, build the cloud step so each Edward alert also gets my $300 order details and an instant paper
copy, even with my Mac off." (2026-10-19)
From the repository root (run `research.edward_live_v1.cloud make-inbox` once first):
  .venv/bin/python cloud/edward_relay_v1/deploy.py --dry-run    # local tests and bundle list; no network
  .venv/bin/python cloud/edward_relay_v1/deploy.py              # install, server tests, keys, paper check, start
  .venv/bin/python cloud/edward_relay_v1/deploy.py --keys-only  # re-send keys (e.g. after `relay setup`), restart
Installs to /opt/edward-relay as its own system user; systemd service edward-relay (always on, restarts itself).
Keys (U036 paper keys from .env; Pushover + inbox from .env.edward) travel on stdin over the pinned SSH connection and
are never printed. Unlike the timer jobs, uncommitted bundle files are allowed; DEPLOYED.json records the git commit,
a dirty flag and each file's SHA-256.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
HOST = "root@198.211.113.234"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=yes",
       "-o", f"UserKnownHostsFile={ROOT / 'research/agentic_shadow_v1/deployment/personal-cloud-known-hosts'}",
       "-o", "IdentitiesOnly=yes", "-i", str(Path.home() / ".ssh/personal_trading_cloud"), HOST]
CODE = [f"research/edward_live_v1/{name}.py" for name in
        ("__init__", "parse", "notify", "copier", "relay", "cloud", "test_edward_live")]
BUNDLE = {**{path: path for path in CODE}, "systemd/edward-relay.service": "cloud/edward_relay_v1/edward-relay.service"}
TESTS = ["research.edward_live_v1.test_edward_live"]
RUN_AS = "cd /tmp && runuser -u edward-relay -- env PYTHONPATH=/opt/edward-relay PYTHONDONTWRITEBYTECODE=1 python3"

INSTALL = r"""set -euo pipefail
python3 -c 'import sys; assert sys.version_info >= (3, 11), sys.version'
id edward-relay >/dev/null 2>&1 || useradd --system --home-dir /opt/edward-relay --no-create-home --shell /usr/sbin/nologin edward-relay
install -d -o root -g root -m 0755 /opt/edward-relay
tar -xzf - -C /opt/edward-relay --no-same-owner --no-same-permissions
chown -R root:root /opt/edward-relay/research /opt/edward-relay/systemd /opt/edward-relay/DEPLOYED.json
find /opt/edward-relay/research /opt/edward-relay/systemd -type d -exec chmod 0755 {} +
find /opt/edward-relay/research /opt/edward-relay/systemd /opt/edward-relay/DEPLOYED.json -type f -exec chmod 0644 {} +
install -d -o edward-relay -g edward-relay -m 0700 /opt/edward-relay/outputs /opt/edward-relay/outputs/edward_live
install -o root -g root -m 0644 /opt/edward-relay/systemd/edward-relay.service /etc/systemd/system/
systemctl daemon-reload
""" + RUN_AS + " -m unittest -q " + " ".join(TESTS) + " 2>&1 | tail -1\n"

SECRETS = r"""
import json, os, pwd, sys
from pathlib import Path
v = json.load(sys.stdin)
assert v["key"] and v["secret"] and v["inbox_topic"] and v["inbox_key"]
user = pwd.getpwnam("edward-relay")
def put(path, text):
    tmp = path.parent / (path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.chown(tmp, user.pw_uid, user.pw_gid)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
root = Path("/opt/edward-relay")
put(root / ".env", "ALPACA_PAPER_API_KEY=%s\nALPACA_PAPER_API_SECRET=%s\n" % (v["key"], v["secret"]))
lines = ["EDWARD_INBOX_TOPIC=%s" % v["inbox_topic"], "EDWARD_INBOX_KEY=%s" % v["inbox_key"]]
if v.get("pushover_token") and v.get("pushover_user"):
    lines += ["PUSHOVER_APP_TOKEN=%s" % v["pushover_token"], "PUSHOVER_USER_KEY=%s" % v["pushover_user"]]
put(root / ".env.edward", "\n".join(lines) + "\n")
print("keys written (values suppressed); pushover:", "yes" if len(lines) > 2 else "not yet")
"""

# Read-only checks as the service user: the paper-account guard, one option quote, and the key files.
SMOKE = RUN_AS + r""" -c '
from research.edward_live_v1.copier import Alpaca
from research.edward_live_v1 import notify
a = Alpaca(); a.guard(); bid, ask = a.quote("QQQ261023P00720000")
cfg = notify.config()
print("paper account ...U036 ok; option quote ok:", ask is not None, "; inbox set:", bool(cfg.get("EDWARD_INBOX_KEY")),
      "; phone channels:", notify.channels(cfg) or "none yet")
'
"""

START = """set -euo pipefail
systemctl enable edward-relay.service >/dev/null 2>&1
systemctl restart edward-relay.service
sleep 4
echo "service: $(systemctl is-active edward-relay.service)"
journalctl -u edward-relay.service -n 3 --no-pager -o cat
"""


def remote(command, data=b""):
    result = subprocess.run(SSH + [command], input=data, capture_output=True, timeout=1200)
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()[-600:]
        raise SystemExit(f"Remote step failed (exit {result.returncode}): {detail}")
    return result.stdout.decode(errors="replace").strip()


def paper_keys(path=ROOT / ".env"):
    vals = {}
    for line in path.read_text().splitlines():
        m = re.fullmatch(r"\s*(?:export\s+)?(ALPACA_PAPER_API_KEY|ALPACA_PAPER_API_SECRET)\s*=\s*(.*?)\s*", line)
        if m:
            vals[m[1]] = m[2].strip("\"'")
    return vals["ALPACA_PAPER_API_KEY"], vals["ALPACA_PAPER_API_SECRET"]


def secrets_payload():
    from research.edward_live_v1 import notify
    cfg = notify.config()
    if not (cfg.get("EDWARD_INBOX_TOPIC") and cfg.get("EDWARD_INBOX_KEY")):
        raise SystemExit("No inbox yet: run `research.edward_live_v1.cloud make-inbox` first")
    key, secret = paper_keys()
    return {"key": key, "secret": secret, "inbox_topic": cfg["EDWARD_INBOX_TOPIC"],
            "inbox_key": cfg["EDWARD_INBOX_KEY"], "pushover_token": cfg.get("PUSHOVER_APP_TOKEN", ""),
            "pushover_user": cfg.get("PUSHOVER_USER_KEY", "")}


def bundle():
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", *BUNDLE.values()], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())
    files = {target: (ROOT / source).read_bytes() for target, source in BUNDLE.items()}
    manifest = {"deployed_at": datetime.now(timezone.utc).isoformat(), "git_commit": commit,
                "bundle_files_uncommitted": dirty,
                "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}}
    files["DEPLOYED.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, raw in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(raw), 0o644, int(datetime.now().timestamp())
            archive.addfile(info, io.BytesIO(raw))
    return buffer.getvalue(), manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keys-only", action="store_true")
    args = parser.parse_args()
    payload = secrets_payload()
    if args.keys_only:
        print("keys:", remote("python3 -c " + shlex.quote(SECRETS), json.dumps(payload).encode()))
        print("start:\n" + remote(START))
        return
    tests = subprocess.run([sys.executable, "-m", "unittest", "-q", *TESTS], cwd=ROOT,
                           env={**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}", "PYTHONDONTWRITEBYTECODE": "1"},
                           capture_output=True, text=True)
    if tests.returncode:
        raise SystemExit("Local tests failed; not deploying")
    archive, manifest = bundle()
    print(json.dumps({"git_commit": manifest["git_commit"], "uncommitted": manifest["bundle_files_uncommitted"],
                      "files": sorted(manifest["files"]), "local_tests": "passed",
                      "pushover_keys": bool(payload["pushover_token"])}, indent=2))
    if args.dry_run:
        print("Dry run: nothing sent.")
        return
    print("1/4 install + server tests:", remote(INSTALL, archive).replace("\n", " | "))
    print("2/4 keys:", remote("python3 -c " + shlex.quote(SECRETS), json.dumps(payload).encode()))
    print("3/4 read-only check:", remote(SMOKE))
    print("4/4 start:\n" + remote(START))


if __name__ == "__main__":
    main()
