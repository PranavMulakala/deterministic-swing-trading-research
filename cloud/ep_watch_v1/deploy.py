"""Deploy the EP forward paper watch (output/EP_FORWARD_WATCH_PLAN_20261005.md) to the personal DigitalOcean server.
Read-only market data and SEC filing times; places no orders.

Owner approval: "yes set up the forward paper watch" (2026-10-05).
From the repository root:
  .venv/bin/python cloud/ep_watch_v1/deploy.py --dry-run   # local checks and bundle list; no network
  .venv/bin/python cloud/ep_watch_v1/deploy.py              # install, tests, live print-only check, enable timers
Installs to /opt/ep-watch as its own system user. Keys (Alpaca data keys from .env.lite, Resend) travel on stdin over the
pinned SSH connection and are never printed. Timers: 10:50 and 17:05 ET, Monday to Friday; the job stops itself after
Feb 12, 2027 (one "finished" email), after which the timers should be disabled.
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
UNITS = [f"ep-watch-{kind}.{ext}" for kind in ("morning", "evening") for ext in ("service", "timer")]
CODE = ["research/ep_watch_v1/__init__.py", "research/ep_watch_v1/watch.py", "research/ep_watch_v1/test_watch.py",
        "research/ep_watch_v1/universe.json",
        "research/ep_test_v1/__init__.py", "research/ep_test_v1/backtest.py", "research/ep_test_v1/candidates.py",
        "research/ep_test_v1/fetch_intraday.py", "research/ep_test_v1/fetch_edgar.py",
        "research/ep_test_v1/test_backtest.py",
        "research/breakout_test_v1/backtest.py", "research/provenance_v1/provenance.py",
        "research/lite_dip_history_v1/run.py", "research/lite_paper_bot_v1/bot.py", "research/lite_paper_bot_v1/news.py",
        "research/real_position_alert_v1/monitor.py"]
BUNDLE = {**{path: path for path in CODE}, **{f"systemd/{u}": f"cloud/ep_watch_v1/{u}" for u in UNITS}}
TIMERS = " ".join(u for u in UNITS if u.endswith(".timer"))
TESTS = ["research.ep_watch_v1.test_watch", "research.ep_test_v1.test_backtest"]

INSTALL = r"""set -euo pipefail
python3 -c 'import sys; assert sys.version_info >= (3, 11), sys.version'
id ep-watch >/dev/null 2>&1 || useradd --system --home-dir /opt/ep-watch --no-create-home --shell /usr/sbin/nologin ep-watch
install -d -o root -g root -m 0755 /opt/ep-watch
tar -xzf - -C /opt/ep-watch --no-same-owner --no-same-permissions
chown -R root:root /opt/ep-watch/research /opt/ep-watch/systemd /opt/ep-watch/DEPLOYED.json
find /opt/ep-watch/research /opt/ep-watch/systemd -type d -exec chmod 0755 {} +
find /opt/ep-watch/research /opt/ep-watch/systemd /opt/ep-watch/DEPLOYED.json -type f -exec chmod 0644 {} +
install -d -o ep-watch -g ep-watch -m 0700 /opt/ep-watch/outputs /opt/ep-watch/outputs/ep_watch
install -o root -g root -m 0644 /opt/ep-watch/systemd/*.service /opt/ep-watch/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/ep-watch-*.service 2>&1 | grep -v '^$' | head -5 || true
cd /tmp && runuser -u ep-watch -- env PYTHONPATH=/opt/ep-watch PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q """ + " ".join(TESTS) + r""" 2>&1 | tail -1
"""

SECRETS = r"""
import json, os, pwd, sys
from pathlib import Path
v = json.load(sys.stdin)
assert v["key"] and v["secret"] and v["resend"].startswith("re_")
user = pwd.getpwnam("ep-watch")
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
root = Path("/opt/ep-watch")
put(root / ".env.lite", "LITE_PAPER_API_KEY=%s\nLITE_PAPER_API_SECRET=%s\n" % (v["key"], v["secret"]))
put(root / ".env", "TRADING_REPORT_RESEND_API_KEY=%s\n" % v["resend"])
print("keys written (values suppressed)")
"""

# A live, print-only run of both jobs on today's market into a scratch folder (real outputs untouched, no email).
SMOKE = r"""set -euo pipefail
cd /tmp && runuser -u ep-watch -- env PYTHONPATH=/opt/ep-watch PYTHONDONTWRITEBYTECODE=1 python3 -c '
from datetime import datetime
from pathlib import Path
from unittest import mock
import tempfile
from research.ep_watch_v1 import watch
today = datetime.now(watch.NY).date().isoformat()
with tempfile.TemporaryDirectory() as tmp, mock.patch.object(watch, "OUT", Path(tmp)), \
        mock.patch.object(watch, "START_DAY", today):
    api, sec = watch.Alpaca(), watch.Sec()
    rows = watch.morning(api, sec, today)
    snap = watch.evening(api, sec, today)
    print("smoke ok:", today, "gap-ups", None if rows is None else len(rows),
          "earnings", None if rows is None else sum(r["earnings"] for r in rows),
          "candidate days", None if snap is None else snap["candidate_days"])
'
"""

ENABLE = f"""set -euo pipefail
systemctl enable --now {TIMERS} >/dev/null 2>&1
systemctl list-timers 'ep-watch-*' --no-pager --no-legend
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
    from research.lite_paper_bot_v1.bot import credentials
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
