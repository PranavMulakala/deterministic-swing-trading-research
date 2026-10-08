"""Deploy the daily LITE chatter email (research/chatter_v1) to the personal DigitalOcean server.
Read-only public feeds (Stocktwits, Reddit RSS) + Alpaca price snapshots; places no orders. Owner approval: "yes build the daily LITE chatter
email" (2026-10-08).
From the repository root:
  .venv/bin/python cloud/chatter_v1/deploy.py --dry-run   # local checks and bundle list; no network
  .venv/bin/python cloud/chatter_v1/deploy.py              # install, tests, live print-only check, enable the timer
Installs to /opt/chatter as its own system user. Keys (the ...U036 paper keys from .env, used only for price snapshots; Resend) travel on stdin over the
pinned SSH connection and are never printed. Timer: 16:15 ET, Monday to Friday.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
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
UNITS = ["chatter.service", "chatter.timer"]
CODE = ["research/chatter_v1/__init__.py", "research/chatter_v1/report.py", "research/chatter_v1/test_report.py",
        "research/covered_call_practice_v1/__init__.py", "research/covered_call_practice_v1/report.py",
        "research/real_position_alert_v1/monitor.py"]
BUNDLE = {**{path: path for path in CODE}, **{f"systemd/{u}": f"cloud/chatter_v1/{u}" for u in UNITS}}
TIMERS = " ".join(u for u in UNITS if u.endswith(".timer"))
TESTS = ["research.chatter_v1.test_report"]

INSTALL = r"""set -euo pipefail
python3 -c 'import sys; assert sys.version_info >= (3, 11), sys.version'
id chatter >/dev/null 2>&1 || useradd --system --home-dir /opt/chatter --no-create-home --shell /usr/sbin/nologin chatter
install -d -o root -g root -m 0755 /opt/chatter
tar -xzf - -C /opt/chatter --no-same-owner --no-same-permissions
chown -R root:root /opt/chatter/research /opt/chatter/systemd /opt/chatter/DEPLOYED.json
find /opt/chatter/research /opt/chatter/systemd -type d -exec chmod 0755 {} +
find /opt/chatter/research /opt/chatter/systemd /opt/chatter/DEPLOYED.json -type f -exec chmod 0644 {} +
install -d -o chatter -g chatter -m 0700 /opt/chatter/outputs /opt/chatter/outputs/chatter
install -o root -g root -m 0644 /opt/chatter/systemd/*.service /opt/chatter/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/chatter.service 2>&1 | grep -v '^$' | head -5 || true
cd /tmp && runuser -u chatter -- env PYTHONPATH=/opt/chatter PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q """ + " ".join(TESTS) + r""" 2>&1 | tail -1
"""

SECRETS = r"""
import json, os, pwd, sys
from pathlib import Path
v = json.load(sys.stdin)
assert v["key"] and v["secret"] and v["resend"].startswith("re_")
user = pwd.getpwnam("chatter")
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
root = Path("/opt/chatter")
put(root / ".env", "ALPACA_PAPER_API_KEY=%s\nALPACA_PAPER_API_SECRET=%s\nTRADING_REPORT_RESEND_API_KEY=%s\n"
    % (v["key"], v["secret"], v["resend"]))
print("keys written (values suppressed)")
"""

# A live, print-only run of both jobs on today's market into a scratch folder (real outputs untouched, no email).
SMOKE = r"""set -euo pipefail
cd /tmp && runuser -u chatter -- env PYTHONPATH=/opt/chatter PYTHONDONTWRITEBYTECODE=1 python3 -c '
from pathlib import Path
from unittest import mock
import tempfile
from research.chatter_v1 import report
with tempfile.TemporaryDirectory() as tmp, mock.patch.object(report, "OUT", Path(tmp)):
    body, rows, day = report.run()
    print("smoke ok:", [(r["symbol"], r["posts"]) for r in rows], "reddit:", "ok" if "WallStreetBets daily thread\n  Not available" not in body else "unavailable")
'
"""

ENABLE = f"""set -euo pipefail
systemctl enable --now {TIMERS} >/dev/null 2>&1
systemctl list-timers chatter.timer --no-pager --no-legend
"""


def remote(command, data=b""):
    result = subprocess.run(SSH + [command], input=data, capture_output=True, timeout=1200)
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()[-600:]
        raise SystemExit(f"Remote step failed (exit {result.returncode}): {detail}")
    return result.stdout.decode(errors="replace").strip()


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    from research.covered_call_practice_v1.report import credentials
    from research.real_position_alert_v1.monitor import resend_key
    tests = subprocess.run([sys.executable, "-m", "unittest", "-q", *TESTS], cwd=ROOT,
                           env={**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}", "PYTHONDONTWRITEBYTECODE": "1"},
                           capture_output=True, text=True)
    if tests.returncode:
        raise SystemExit("Local tests failed; not deploying")
    key, secret = credentials()
    resend = resend_key()
    archive, manifest = bundle()
    if manifest["bundle_files_uncommitted"]:
        raise SystemExit("Commit the bundle files first (the deploy manifest must point at committed code)")
    print(json.dumps({"git_commit": manifest["git_commit"], "files": sorted(manifest["files"]),
                      "local_tests": "passed", "keys_present": True}, indent=2))
    if args.dry_run:
        print("Dry run: nothing sent.")
        return
    print("1/4 install + server tests:", remote(INSTALL, archive).replace("\n", " | "))
    payload = json.dumps({"key": key, "secret": secret, "resend": resend}).encode()
    print("2/4 keys:", remote("python3 -c " + shlex.quote(SECRETS), payload))
    print("3/4 live print-only check:", remote(SMOKE).replace("\n", " | "))
    print("4/4 timers:\n" + remote(ENABLE))


if __name__ == "__main__":
    main()
