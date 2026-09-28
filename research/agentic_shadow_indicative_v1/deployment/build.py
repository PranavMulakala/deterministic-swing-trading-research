"""Build an allowlisted producer/consumer release with no credentials."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

root = Path(__file__).resolve().parents[3]
source = root / "research/agentic_shadow_indicative_v1"
out = Path(sys.argv[1]).resolve()
if out.exists():
    raise SystemExit("Use a new empty release path")
out.mkdir(parents=True)
for name in ("engine.py", "fixtures.py", "report.py", "run.py", "producer.py", "checkpoint.py",
             "config.json", "PROTOCOL.md", "FREEZE.json", "README.md", "__init__.py"):
    target = out / "research/agentic_shadow_indicative_v1" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / name, target)
for name in ("safe_paths.py", "__init__.py"):
    target = out / "src/swingbot" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "src/swingbot" / name, target)
for name in ("verify_release.py", "validate_credentials.py", "install.sh", "upgrade.sh", "rollback.sh",
             "trading-shadow-indicative-producer.service",
             "trading-shadow-indicative-smoke.service",
             "trading-shadow-indicative-producer.timer",
             "trading-shadow-indicative-consumer.service",
             "trading-shadow-indicative.path"):
    shutil.copyfile(source / "deployment" / name, out / name)
shutil.copyfile(source / "deployment" / "README.md", out / "DEPLOYMENT.md")
shutil.copyfile(source / "deployment" / "DEPLOY_CHECKLIST.md", out / "DEPLOY_CHECKLIST.md")
files = {str(path.relative_to(out)): hashlib.sha256(path.read_bytes()).hexdigest()
         for path in sorted(out.rglob("*")) if path.is_file()}
revision = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
manifest = {
    "revision": revision,
    "files": files,
    "orders": False,
    "credentials_included": False,
    "purpose": "plumbing_only",
    "options_feed": "alpaca-indicative",
}
(out / "RELEASE.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(revision)
