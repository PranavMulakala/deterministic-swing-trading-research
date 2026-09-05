import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swingbot.data import DataError, load_universe, write_symbol_csv


class DataTests(unittest.TestCase):
    def test_changed_pinned_file_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            csv_path = folder / "SPY.csv"
            rows = [{"date": "2026-01-02", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
            write_symbol_csv(csv_path, rows)
            (folder / "manifest.json").write_text(json.dumps({
                "files": {"SPY": {"path": "SPY.csv", "sha256": "wrong"}}
            }), encoding="utf-8")
            with self.assertRaisesRegex(DataError, "checksum mismatch"):
                load_universe({"universe": ["SPY"]}, folder)


if __name__ == "__main__":
    unittest.main()
