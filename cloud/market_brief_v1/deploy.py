"""Deploy the daily market brief to the personal DigitalOcean server. Read-only market data; places no orders.

Owner approval: "yes go ahead and scehudle it" (2026-10-02), for the 16:30 ET weekday brief email.
From the repository root:
  .venv/bin/python cloud/market_brief_v1/deploy.py --dry-run   # local checks and bundle list; no network
  .venv/bin/python cloud/market_brief_v1/deploy.py              # install, test, one print-only run, enable timer
Installs to /opt/market-brief as its own system user. Keys (Alpaca data keys from .env.lite, Resend) travel on stdin
over the pinned SSH connection and are never printed. After a real buy or sell, edit
research/market_brief_v1/positions.json and run this again.
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
UNITS = ["market-brief.service", "market-brief.timer"]
CODE = ["research/market_brief_v1/brief.py", "research/market_brief_v1/test_brief.py",
        "research/market_brief_v1/positions.json", "research/market_brief_v1/calendar.json",
        "research/lite_paper_bot_v1/bot.py", "research/lite_paper_bot_v1/news.py",
        "research/lite_dip_history_v1/run.py", "research/real_position_alert_v1/monitor.py"]
BUNDLE = {**{path: path for path in CODE}, **{f"systemd/{u}": f"cloud/market_brief_v1/{u}" for u in UNITS}}
TIMERS = " ".join(u for u in UNITS if u.endswith(".timer"))

INSTALL = r"""set -euo pipefail
python3 -c 'import sys; assert sys.version_info >= (3, 11), sys.version'
id brief-bot >/dev/null 2>&1 || useradd --system --home-dir /opt/market-brief --no-create-home --shell /usr/sbin/nologin brief-bot
install -d -o root -g root -m 0755 /opt/market-brief
tar -xzf - -C /opt/market-brief --no-same-owner --no-same-permissions
chown -R root:root /opt/market-brief/research /opt/market-brief/systemd /opt/market-brief/DEPLOYED.json
find /opt/market-brief/research /opt/market-brief/systemd -type d -exec chmod 0755 {} +
find /opt/market-brief/research /opt/market-brief/systemd /opt/market-brief/DEPLOYED.json -type f -exec chmod 0644 {} +
install -o root -g root -m 0644 /opt/market-brief/systemd/*.service /opt/market-brief/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/market-brief*.service 2>&1 | grep -v '^$' | head -5 || true
cd /tmp && runuser -u brief-bot -- env PYTHONPATH=/opt/market-brief PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q research.market_brief_v1.test_brief 2>&1 | tail -1
"""

SECRETS = r"""
import json, os, pwd, sys
from pathlib import Path
v = json.load(sys.stdin)
assert v["key"] and v["secret"] and v["resend"].startswith("re_")
user = pwd.getpwnam("brief-bot")
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
root = Path("/opt/market-brief")
put(root / ".env.lite", "LITE_PAPER_API_KEY=%s\nLITE_PAPER_API_SECRET=%s\n" % (v["key"], v["secret"]))
put(root / ".env", "TRADING_REPORT_RESEND_API_KEY=%s\n" % v["resend"])
print("keys written (values suppressed)")
"""

TEST_RUN = r"""set -euo pipefail
cd /opt/market-brief && runuser -u brief-bot -- env PYTHONPATH=/opt/market-brief PYTHONDONTWRITEBYTECODE=1 python3 -m research.market_brief_v1.brief | head -12
"""

ENABLE = f"""set -euo pipefail
systemctl enable --now {TIMERS} >/dev/null 2>&1
systemctl list-timers 'market-brief*' --no-pager --no-legend
"""


def remote(command, data=b""):
    result = subprocess.run(SSH + [command], input=data, capture_output=True, timeout=900)
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
    tests = subprocess.run([sys.executable, "-m", "unittest", "-q", "research.market_brief_v1.test_brief"],
                           cwd=ROOT, env={**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}",
                                          "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
    if tests.returncode:
        raise SystemExit("Local brief tests failed; not deploying")
    key, secret = credentials()
    resend = resend_key()
    archive, manifest = bundle()
    print(json.dumps({"git_commit": manifest["git_commit"], "bundle_files_uncommitted": manifest["bundle_files_uncommitted"],
                      "files": sorted(manifest["files"]), "local_tests": "passed", "keys_present": True}, indent=2))
    if args.dry_run:
        print("Dry run: nothing sent.")
        return
    print("1/4 install:", remote(INSTALL, archive).replace("\n", " | "))
    payload = json.dumps({"key": key, "secret": secret, "resend": resend}).encode()
    print("2/4 keys:", remote("python3 -c " + shlex.quote(SECRETS), payload))
    print("3/4 server test run (print only, no email):", remote(TEST_RUN).replace("\n", " | "))
    print("4/4 timers:\n" + remote(ENABLE))


if __name__ == "__main__":
    main()
