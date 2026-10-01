"""Deploy the paper small-cap scanner to the personal DigitalOcean server. Read-only market data; places no orders.

Owner approval: "yes schedule it on the cloud and can you make this run i dont want to touch it" (2026-10-01).
From the repository root:
  .venv/bin/python cloud/smallcap_scanner_v1/deploy.py --dry-run   # local checks and bundle list; no network
  .venv/bin/python cloud/smallcap_scanner_v1/deploy.py              # install, test, one live scan, enable timers
Installs to /opt/smallcap-scanner as its own system user. Keys (Alpaca data keys from .env.lite, Resend, Alpha
Vantage) travel on stdin over the pinned SSH connection and are never printed.
Timers: scans every 5 minutes 07:00-10:00 ET, watch-list email 10:05 ET, review email 16:15 ET, Monday to Friday.
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
UNITS = [f"smallcap-scanner-{kind}.{ext}" for kind in ("scan", "summary", "review") for ext in ("service", "timer")]
CODE = ["research/smallcap_scanner_v1/scanner.py", "research/smallcap_scanner_v1/test_scanner.py",
        "research/lite_paper_bot_v1/bot.py", "research/lite_paper_bot_v1/news.py",
        "research/lite_dip_history_v1/run.py", "research/breakout_test_v1/fetch.py",
        "research/real_position_alert_v1/monitor.py"]
BUNDLE = {**{path: path for path in CODE}, **{f"systemd/{u}": f"cloud/smallcap_scanner_v1/{u}" for u in UNITS}}
TIMERS = " ".join(u for u in UNITS if u.endswith(".timer"))

INSTALL = r"""set -euo pipefail
python3 -c 'import sys; assert sys.version_info >= (3, 11), sys.version'
id scanner-bot >/dev/null 2>&1 || useradd --system --home-dir /opt/smallcap-scanner --no-create-home --shell /usr/sbin/nologin scanner-bot
install -d -o root -g root -m 0755 /opt/smallcap-scanner
tar -xzf - -C /opt/smallcap-scanner --no-same-owner --no-same-permissions
chown -R root:root /opt/smallcap-scanner/research /opt/smallcap-scanner/systemd /opt/smallcap-scanner/DEPLOYED.json
find /opt/smallcap-scanner/research /opt/smallcap-scanner/systemd -type d -exec chmod 0755 {} +
find /opt/smallcap-scanner/research /opt/smallcap-scanner/systemd /opt/smallcap-scanner/DEPLOYED.json -type f -exec chmod 0644 {} +
install -d -o scanner-bot -g scanner-bot -m 0700 /opt/smallcap-scanner/outputs /opt/smallcap-scanner/outputs/smallcap_scanner
install -o root -g root -m 0644 /opt/smallcap-scanner/systemd/*.service /opt/smallcap-scanner/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/smallcap-scanner-*.service 2>&1 | grep -v '^$' | head -5 || true
cd /tmp && runuser -u scanner-bot -- env PYTHONPATH=/opt/smallcap-scanner PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q research.smallcap_scanner_v1.test_scanner 2>&1 | tail -1
"""

SECRETS = r"""
import json, os, pwd, sys
from pathlib import Path
v = json.load(sys.stdin)
assert v["key"] and v["secret"] and v["resend"].startswith("re_")
user = pwd.getpwnam("scanner-bot")
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
root = Path("/opt/smallcap-scanner")
put(root / ".env.lite", "LITE_PAPER_API_KEY=%s\nLITE_PAPER_API_SECRET=%s\n" % (v["key"], v["secret"]))
put(root / ".env", "TRADING_REPORT_RESEND_API_KEY=%s\n" % v["resend"])
if v.get("news"):
    put(root / ".env.news", "ALPHAVANTAGE_API_KEY=%s\n" % v["news"])
print("keys written (values suppressed)")
"""

TEST_RUN = r"""set -euo pipefail
systemctl start smallcap-scanner-scan.service
journalctl -u smallcap-scanner-scan.service -n 3 --no-pager --output=cat | head -3
"""

ENABLE = f"""set -euo pipefail
systemctl enable --now {TIMERS} >/dev/null 2>&1
systemctl list-timers 'smallcap-scanner-*' --no-pager --no-legend
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
    from research.lite_paper_bot_v1.news import api_key as news_key
    from research.real_position_alert_v1.monitor import resend_key
    tests = subprocess.run([sys.executable, "-m", "unittest", "-q", "research.smallcap_scanner_v1.test_scanner"],
                           cwd=ROOT, env={**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}",
                                          "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
    if tests.returncode:
        raise SystemExit("Local scanner tests failed; not deploying")
    key, secret = credentials()
    resend, news = resend_key(), news_key() or ""
    archive, manifest = bundle()
    print(json.dumps({"git_commit": manifest["git_commit"], "bundle_files_uncommitted": manifest["bundle_files_uncommitted"],
                      "files": sorted(manifest["files"]), "local_tests": "passed", "keys_present": True,
                      "alpha_vantage_key": bool(news)}, indent=2))
    if args.dry_run:
        print("Dry run: nothing sent.")
        return
    print("1/4 install:", remote(INSTALL, archive).replace("\n", " | "))
    payload = json.dumps({"key": key, "secret": secret, "resend": resend, "news": news}).encode()
    print("2/4 keys:", remote("python3 -c " + shlex.quote(SECRETS), payload))
    print("3/4 server test scan:", remote(TEST_RUN).replace("\n", " | "))
    print("4/4 timers:\n" + remote(ENABLE))


if __name__ == "__main__":
    main()
