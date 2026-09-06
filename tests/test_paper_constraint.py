import contextlib
import io
import json
from pathlib import Path
import unittest

from swingbot.cli import analyze_paper_constraint


ROOT = Path(__file__).parents[1]


class WholeShareConstraintTests(unittest.TestCase):
    def test_post_hoc_diagnostic_reproduces_declared_values(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            analyze_paper_constraint(ROOT)
        result = json.loads(output.getvalue())
        self.assertEqual(
            result["classification"],
            "post_hoc_execution_feasibility_diagnostic_not_preregistered",
        )
        out_of_sample = result["results"]["out_of_sample"]
        self.assertAlmostEqual(out_of_sample["final_equity"], 587.29064967, places=8)
        self.assertEqual(out_of_sample["trade_count"], 395)
        self.assertEqual(out_of_sample["zero_quantity_rejections"], 713)
        self.assertAlmostEqual(out_of_sample["max_drawdown_pct"], 3.82387953, places=8)


if __name__ == "__main__":
    unittest.main()
