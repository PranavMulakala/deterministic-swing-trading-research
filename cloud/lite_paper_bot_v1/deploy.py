"""Deploy the LITE paper dip bot to the personal DigitalOcean server. Paper trading only.

Owner approval: "yes deploy" (2026-09-28). From the repository root:
  .venv/bin/python cloud/lite_paper_bot_v1/deploy.py --dry-run   # local checks and bundle list; no network
  .venv/bin/python cloud/lite_paper_bot_v1/deploy.py              # install, test, retire the Mac job, enable
Order: install code and secrets; run the bot once on the server outside the entry window; only if that run
is clean, disable the Mac job (plus a local KILL file) and then enable the server timer, so only one copy
ever trades. Secrets travel on stdin over the pinned SSH connection and are never printed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
NY = ZoneInfo("America/New_York")
HOST = "root@198.211.113.234"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=yes",
       "-o", f"UserKnownHostsFile={ROOT / 'research/agentic_shadow_v1/deployment/personal-cloud-known-hosts'}",
       "-o", "IdentitiesOnly=yes", "-i", str(Path.home() / ".ssh/personal_trading_cloud"), HOST]
BUNDLE = {
    "research/lite_paper_bot_v1/bot.py": "research/lite_paper_bot_v1/bot.py",
    "research/lite_paper_bot_v1/PROTOCOL.md": "research/lite_paper_bot_v1/PROTOCOL.md",
    "research/lite_paper_bot_v1/test_bot.py": "research/lite_paper_bot_v1/test_bot.py",
    "research/real_position_alert_v1/monitor.py": "research/real_position_alert_v1/monitor.py",
    "systemd/lite-paper-bot.service": "cloud/lite_paper_bot_v1/lite-paper-bot.service",
    "systemd/lite-paper-bot.timer": "cloud/lite_paper_bot_v1/lite-paper-bot.timer",
}
LOCAL_JOB = "com.pranav.lite-paper-bot"
CLEAN_TEST = {"MARKET_CLOSED", "LATE_START", "NO_STANDARD_SESSION"}

INSTALL = r"""set -euo pipefail
python3 -c 'import sys; assert sys.version_info >= (3, 11), sys.version'
id lite-bot >/dev/null 2>&1 || useradd --system --home-dir /opt/lite-paper-bot --no-create-home --shell /usr/sbin/nologin lite-bot
install -d -o root -g root -m 0755 /opt/lite-paper-bot
tar -xzf - -C /opt/lite-paper-bot --no-same-owner --no-same-permissions
chown -R root:root /opt/lite-paper-bot/research /opt/lite-paper-bot/systemd /opt/lite-paper-bot/DEPLOYED.json
find /opt/lite-paper-bot/research /opt/lite-paper-bot/systemd -type d -exec chmod 0755 {} +
find /opt/lite-paper-bot/research /opt/lite-paper-bot/systemd /opt/lite-paper-bot/DEPLOYED.json -type f -exec chmod 0644 {} +
install -d -o lite-bot -g lite-bot -m 0700 /opt/lite-paper-bot/outputs /opt/lite-paper-bot/outputs/lite_paper_bot
install -o root -g root -m 0644 /opt/lite-paper-bot/systemd/lite-paper-bot.service /opt/lite-paper-bot/systemd/lite-paper-bot.timer /etc/systemd/system/
systemctl daemon-reload
cd /tmp && runuser -u lite-bot -- env PYTHONPATH=/opt/lite-paper-bot PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q research.lite_paper_bot_v1.test_bot 2>&1 | tail -1
echo "NTP synchronized: $(timedatectl show -p NTPSynchronized --value)"
"""

SECRETS = r"""
import json, os, pwd, sys
from pathlib import Path
v = json.load(sys.stdin)
assert v["key"] and v["secret"] and v["resend"].startswith("re_") and json.loads(v["state"])["account_id"]
user = pwd.getpwnam("lite-bot")
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
root = Path("/opt/lite-paper-bot")
put(root / ".env.lite", "LITE_PAPER_API_KEY=%s\nLITE_PAPER_API_SECRET=%s\n" % (v["key"], v["secret"]))
put(root / ".env", "TRADING_REPORT_RESEND_API_KEY=%s\n" % v["resend"])
state = root / "outputs/lite_paper_bot/state.json"
if state.exists():
    print("keys written (values suppressed); existing server state kept")
else:
    put(state, v["state"])
    print("keys written (values suppressed); bot bind copied")
"""

TEST_RUN = r"""set -euo pipefail
systemctl start lite-paper-bot.service || true
tail -n 1 /opt/lite-paper-bot/outputs/lite_paper_bot/events.jsonl
"""

ENABLE = r"""set -euo pipefail
systemctl enable --now lite-paper-bot.timer >/dev/null 2>&1
systemctl list-timers lite-paper-bot.timer --no-pager --no-legend
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
    now = datetime.now(NY)
    if now.weekday() < 5 and time(9, 25) <= now.time() <= time(10, 10):
        raise SystemExit("Not deploying between 09:25 and 10:10 ET on a weekday: the Mac copy may be trading.")
    from research.lite_paper_bot_v1.bot import OUT, credentials
    from research.real_position_alert_v1.monitor import resend_key
    tests = subprocess.run([sys.executable, "-m", "unittest", "-q", "research.lite_paper_bot_v1.test_bot"],
                           cwd=ROOT, env={**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}",
                                          "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
    if tests.returncode:
        raise SystemExit("Local bot tests failed; not deploying")
    key, secret = credentials()
    resend = resend_key()
    state = (OUT / "state.json").read_text()
    if not json.loads(state).get("account_id"):
        raise SystemExit("Local bot is not bound; run --bind first")
    archive, manifest = bundle()
    print(json.dumps({"git_commit": manifest["git_commit"], "bundle_files_uncommitted": manifest["bundle_files_uncommitted"],
                      "files": sorted(manifest["files"]), "local_tests": "passed", "keys_present": True,
                      "bound": True}, indent=2))
    if args.dry_run:
        print("Dry run: nothing sent.")
        return
    print("1/5 install:", remote(INSTALL, archive).replace("\n", " | "))
    payload = json.dumps({"key": key, "secret": secret, "resend": resend, "state": state}).encode()
    print("2/5 keys:", remote("python3 -c " + shlex.quote(SECRETS), payload))
    last = json.loads(remote(TEST_RUN))
    print("3/5 server test run:", last.get("type"), "-", str(last.get("detail", ""))[:120])
    if last.get("type") not in CLEAN_TEST:
        raise SystemExit("Server test run was not clean; the Mac job stays active and the server timer is NOT enabled")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LOCAL_JOB}"], capture_output=True)
    subprocess.run(["launchctl", "disable", f"gui/{uid}/{LOCAL_JOB}"], check=True)
    (OUT / "KILL").write_text(f"{datetime.now(timezone.utc).isoformat()} Moved to the cloud server "
                              f"(/opt/lite-paper-bot on {HOST.split('@')[1]}); do not run locally.\n")
    print("4/5 Mac job disabled; local KILL file written so the laptop copy can never trade")
    print("5/5 server timer:", remote(ENABLE))


if __name__ == "__main__":
    main()
