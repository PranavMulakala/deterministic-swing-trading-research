"""Build the single-file QuantConnect algorithm for test #7 (qc_template.py + schedule.json -> qc_main.py).

  PYTHONPATH=src:. .venv/bin/python -m research.earnings_straddle_v1.build_qc
"""
from datetime import date
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent


def to36(n):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        n, r = divmod(n, 36)
        out = digits[r] + out
        if not n:
            return out


def main():
    rows = json.loads((HERE / "schedule.json").read_text())
    base, packed = date(2012, 1, 1), {}
    for symbol, entry, last, timing, _ in rows:
        e, l = date.fromisoformat(entry), date.fromisoformat(last)
        gap, offset = (l - e).days, (l - base).days
        assert 0 < gap <= 9 and 0 <= offset < 36 ** 3
        token = f"{to36(offset):0>3}{gap}{'p' if timing == 'pre' else 'a'}"
        packed.setdefault(symbol, []).append(token)
    literal = "{\n" + "".join(f'    "{s}": "{" ".join(v)}",\n' for s, v in sorted(packed.items())) + "}"
    source = (HERE / "qc_template.py").read_text().replace("__SCHEDULE__", literal)
    assert len(source) < 32000, len(source)
    (HERE / "qc_main.py").write_text(source)
    print(len(rows), "events;", len(source), "bytes ->", HERE / "qc_main.py")


if __name__ == "__main__":
    main()
