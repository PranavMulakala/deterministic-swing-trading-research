"""Validate a dedicated Alpaca credential file without displaying values."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
sys.path[:0] = [str(root / "src"), str(root)]

from research.agentic_shadow_indicative_v1.producer import credentials

if len(sys.argv) != 2:
    raise SystemExit("usage: validate_credentials.py /path/to/alpaca.env")
credentials(Path(sys.argv[1]))
print("Dedicated Alpaca credential file validated: two expected keys, private mode")

