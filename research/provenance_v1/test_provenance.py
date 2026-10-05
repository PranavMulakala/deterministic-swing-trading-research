"""Offline tests for the provenance manifest and the same-bar ambiguity counter."""
import json
import tempfile
import unittest
from pathlib import Path

from research.provenance_v1.provenance import manifest, same_bar_ambiguity, sha256, write_manifest


class ProvenanceTest(unittest.TestCase):
    def test_hash_changes_when_data_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text("a,b\n1,2\n")
            before = sha256(path)
            path.write_text("a,b\n1,3\n")
            self.assertNotEqual(before, sha256(path))

    def test_manifest_records_code_and_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "bars.csv"
            data.write_text("x\n")
            result = Path(tmp) / "result.json"
            result.write_text("{}")
            out = write_manifest(result, code=[__file__], data=[data], params={"dip": 1.0})
            record = json.loads(out.read_text())
            kinds = sorted(v["kind"] for v in record["files"].values())
            self.assertEqual(kinds, ["code", "data"])
            self.assertEqual(record["params"], {"dip": 1.0})
            self.assertEqual(len(record["git_commit"]), 40)

    def test_ambiguity_counts_only_first_touching_bar(self):
        trades = [
            {"stop": 95, "target": 105, "bars": [{"h": 101, "l": 99, "c": 100}, {"h": 106, "l": 94, "c": 100}]},  # ambiguous
            {"stop": 95, "target": 105, "bars": [{"h": 106, "l": 99, "c": 105}, {"h": 107, "l": 90, "c": 95}]},   # target first
            {"stop": 95, "target": 105, "bars": [{"h": 101, "l": 94, "c": 96}]},                                  # stop first
            {"stop": 95, "target": 105, "bars": [{"h": 101, "l": 99, "c": 100}]},                                 # neither
        ]
        result = same_bar_ambiguity(trades)
        self.assertEqual((result["trades"], result["ambiguous"]), (4, 1))
        self.assertAlmostEqual(result["ambiguity_rate"], 0.25)


if __name__ == "__main__":
    unittest.main()
