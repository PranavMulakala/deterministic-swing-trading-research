from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .backtest import BacktestEngine, output_hashes, write_result
from .benchmarks import write_benchmarks
from .config import config_sha256, load_config
from .data import download_universe, load_universe
from .report import write_dashboard, write_milestone_report
from .validation import validate_results


def _paths(root: Path) -> tuple[Path, Path, Path]:
    return root / "config/strategy_v1.json", root / "data/pinned", root / "outputs/v1"


def fetch(root: Path) -> None:
    config_path, data_dir, _ = _paths(root)
    config = load_config(config_path)
    manifest = download_universe(config, data_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))


def reproduce(root: Path) -> None:
    config_path, data_dir, output_dir = _paths(root)
    config = load_config(config_path)
    bars = load_universe(config, data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_cfg = config["data"]
    ranges = {
        "in_sample": (date.fromisoformat(data_cfg["start_date"]), date.fromisoformat(data_cfg["in_sample_end"])),
        "out_of_sample": (date.fromisoformat(data_cfg["out_of_sample_start"]), date.fromisoformat(data_cfg["end_date"])),
    }
    summaries: dict[str, object] = {}
    results = []
    for split, (start, end) in ranges.items():
        run_id = f"{config['strategy_id']}-{split}-{config_sha256(config_path)[:12]}"
        result = BacktestEngine(config, bars, split=split, start_date=start, end_date=end, run_id=run_id).run()
        results.append(result)
        summaries[split] = {
            "strategy": write_result(result, output_dir),
            "benchmarks": write_benchmarks(bars, config, start, end, output_dir, split),
        }
    (output_dir / "run_summary.json").write_text(
        json.dumps({"config_sha256": config_sha256(config_path), "results": summaries}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    validate_results(results, output_dir)
    write_dashboard(output_dir)
    write_milestone_report(output_dir)
    hashes = output_hashes(output_dir)
    (output_dir / "artifact_hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summaries, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic paper-only ETF swing research")
    parser.add_argument("command", choices=("fetch-data", "reproduce"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if args.command == "fetch-data":
        fetch(args.root.resolve())
    else:
        reproduce(args.root.resolve())


if __name__ == "__main__":
    main()
