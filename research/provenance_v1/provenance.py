"""Two small testing upgrades taken from the Oct 4 Reddit deep dive (output/REDDIT_BATCH1_DEEP_DIVE_20261004.md).

1. Provenance manifest: pin a result to the exact code AND data it came from (SHA-256 of every file, the git commit,
   and whether any of those files had uncommitted edits), so "what changed since that result?" has a factual answer.
2. Same-bar ambiguity: for strategies with both a stop and a target, measure how often both are touched inside one
   bar, where a bar-based backtest has to guess the order. Report it as two numbers (ambiguity rate, and the share of
   ambiguous trades whose outcome flips under the opposite assumption) instead of a single "precision" figure.

  from research.provenance_v1.provenance import write_manifest, same_bar_ambiguity
  write_manifest("output/x-results.json", code=["research/x/run.py"], data=["outputs/x/data.csv.gz"], params={...})
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def manifest(code, data, params=None):
    files = {}
    for kind, paths in (("code", code), ("data", data)):
        for p in paths:
            path = (ROOT / p) if not Path(p).is_absolute() else Path(p)
            rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
            files[rel] = {"kind": kind, "bytes": path.stat().st_size, "sha256": sha256(path)}
    code_paths = [p for p, v in files.items() if v["kind"] == "code"]
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git("rev-parse", "HEAD"),
        "code_uncommitted": bool(git("status", "--porcelain", "--", *code_paths)) if code_paths else False,
        "params": params or {},
        "files": files,
    }


def write_manifest(result_path, code, data, params=None):
    """Write <result>.provenance.json next to a result file and return its path."""
    result = Path(result_path)
    out = result.with_name(result.name + ".provenance.json")
    out.write_text(json.dumps(manifest(code, data, params), indent=2) + "\n")
    return out


def same_bar_ambiguity(trades):
    """trades: iterable of dicts with 'bars' (list of {'h','l','c'} after entry), 'stop', 'target', 'side' ('long').
    Returns counts and the two rates. A trade is ambiguous if the FIRST bar that touches either level touches both.
    'flips' counts ambiguous trades whose result differs between stop-first and target-first assumptions, which for
    a plain stop/target exit is every ambiguous trade; it's kept separate so richer exit logic can report fewer."""
    total = ambiguous = flips = 0
    for trade in trades:
        total += 1
        stop, target = trade["stop"], trade["target"]
        for bar in trade["bars"]:
            hit_stop, hit_target = bar["l"] <= stop, bar["h"] >= target
            if hit_stop or hit_target:
                if hit_stop and hit_target:
                    ambiguous += 1
                    flips += 1
                break
    return {"trades": total, "ambiguous": ambiguous, "flips": flips,
            "ambiguity_rate": ambiguous / total if total else None,
            "flip_rate_among_ambiguous": flips / ambiguous if ambiguous else None}
