from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest

from swingbot.paper_dashboard import write_paper_dashboard


class PaperDashboardTests(unittest.TestCase):
    def test_dashboard_escapes_payload_and_redacts_identifiers(self) -> None:
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "status.html"
            write_paper_dashboard(
                {"paper_only": True, "account_id": "paper-account-1234"},
                [
                    {
                        "seq": 1,
                        "occurred_at": "2026-01-01T00:00:00+00:00",
                        "event_type": "test<script>",
                        "payload": {
                            "account_id": "paper-account-1234",
                            "session_id": "private-session",
                            "reason": "<script>alert(1)</script>",
                        },
                    }
                ],
                destination,
            )
            rendered = destination.read_text(encoding="utf-8")
            self.assertIn("test&lt;script&gt;", rendered)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
            self.assertNotIn("paper-account-1234", rendered)
            self.assertNotIn("private-session", rendered)
            self.assertIn("[REDACTED]...1234", rendered)
            self.assertEqual(os.stat(destination).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(destination.parent).st_mode & 0o777, 0o700)

    def test_dashboard_refuses_symbolic_link_destination(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.html"
            target.write_text("unchanged", encoding="utf-8")
            destination = root / "status.html"
            destination.symlink_to(target)
            with self.assertRaisesRegex(PermissionError, "symbolic link"):
                write_paper_dashboard({}, [], destination)
            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")

    def test_dashboard_refuses_symbolic_link_ancestor(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            actual = root / "actual"
            actual.mkdir()
            alias = root / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(PermissionError, "symbolic link"):
                write_paper_dashboard({}, [], alias / "status.html")
            self.assertFalse((actual / "status.html").exists())


if __name__ == "__main__":
    unittest.main()
