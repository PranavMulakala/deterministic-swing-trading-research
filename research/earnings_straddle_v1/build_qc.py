"""Build the single-file QuantConnect algorithm for test #7 (qc_template.py + schedule.json -> qc_main.py).

  PYTHONPATH=src:. .venv/bin/python -m research.earnings_straddle_v1.build_qc
"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent


def main():
    rows = json.loads((HERE / "schedule.json").read_text())
    lines = "\n".join(f"{s},{e.replace('-', '')},{l.replace('-', '')},{'p' if t == 'pre' else 'a'}" for s, e, l, t, _ in rows)
    source = (HERE / "qc_template.py").read_text().replace("__SCHEDULE__", "\n" + lines + "\n")
    (HERE / "qc_main.py").write_text(source)
    print(len(rows), "events;", len(source), "bytes ->", HERE / "qc_main.py")


if __name__ == "__main__":
    main()
