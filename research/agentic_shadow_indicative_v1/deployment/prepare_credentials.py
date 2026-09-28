"""Create a new private two-key credential file from the shared local .env."""
from pathlib import Path
import os
import stat
import sys

from swingbot.safe_paths import require_no_symlink_components

KEYS = ("ALPACA_PAPER_API_KEY", "ALPACA_PAPER_API_SECRET")

if len(sys.argv) != 3:
    raise SystemExit("usage: prepare_credentials.py SOURCE_ENV NEW_OUTPUT")
source = require_no_symlink_components(Path(sys.argv[1]), label="source credentials")
output = require_no_symlink_components(Path(sys.argv[2]), label="prepared credentials")
metadata = source.stat()
if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
        or metadata.st_mode & 0o077 or metadata.st_size > 64 * 1024):
    raise SystemExit("source credential file must be a private regular file")
values = {}
for raw in source.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = (part.strip() for part in line.split("=", 1))
    if key in KEYS:
        if key in values or not value:
            raise SystemExit("duplicate or empty Alpaca credential")
        values[key] = value
if set(values) != set(KEYS):
    raise SystemExit("both Alpaca credentials are required")
if output.exists():
    raise SystemExit("output credential file must not already exist")
output.parent.mkdir(parents=True, exist_ok=True)
descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
try:
    payload = "".join(f"{key}={values[key]}\n" for key in KEYS).encode()
    os.write(descriptor, payload)
    os.fsync(descriptor)
finally:
    os.close(descriptor)
print("Prepared private Alpaca credential file without displaying values")

