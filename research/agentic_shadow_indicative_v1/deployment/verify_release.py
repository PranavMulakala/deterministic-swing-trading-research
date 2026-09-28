from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
manifest = json.loads((root / "RELEASE.json").read_text())
actual_revision = hashlib.sha256(json.dumps(manifest["files"], sort_keys=True,
                                            separators=(",", ":")).encode()).hexdigest()
if (actual_revision != manifest["revision"] or manifest.get("orders") is not False
        or manifest.get("credentials_included") is not False
        or manifest.get("purpose") != "plumbing_only"
        or manifest.get("options_feed") != "alpaca-indicative"):
    raise SystemExit("Indicative release manifest identity failure")
actual_files = {str(path.relative_to(root)) for path in root.rglob("*")
                if path.is_file() and path.name != "RELEASE.json"}
if actual_files != set(manifest["files"]):
    raise SystemExit("Indicative release contains missing or unlisted files")
for name, expected in manifest["files"].items():
    member = Path(name)
    if member.is_absolute() or ".." in member.parts:
        raise SystemExit("Invalid release path")
    path = root / member
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit("Indicative release integrity failure")
producer = (root / "research/agentic_shadow_indicative_v1/producer.py").read_text()
for forbidden in ('method="POST"', 'method="PUT"', 'method="PATCH"',
                  'method="DELETE"', "/v2/orders", "/v2/positions"):
    if forbidden in producer:
        raise SystemExit("Mutating broker capability found in producer")
print("Indicative release verified:", manifest["revision"])

