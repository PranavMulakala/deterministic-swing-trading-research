import argparse
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swingbot.paper_cli import _load_env, add_paper_parser


class PaperCliTests(unittest.TestCase):
    def tearDown(self) -> None:
        for key in ("ALPACA_PAPER_API_KEY", "ALPACA_PAPER_API_SECRET"):
            os.environ.pop(key, None)

    def test_env_requires_private_permissions_and_known_keys(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("ALPACA_PAPER_API_KEY=paper-only\n", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                _load_env(path)
            path.chmod(0o600)
            _load_env(path)
            self.assertEqual(os.environ["ALPACA_PAPER_API_KEY"], "paper-only")
            path.write_text("UNEXPECTED_KEY=value\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                _load_env(path)
            path.write_text("SWINGBOT_KILL_SWITCH=0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected .env key"):
                _load_env(path)

    def test_env_values_are_not_shell_evaluated(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("ALPACA_PAPER_API_SECRET=$(not-a-command)\n", encoding="utf-8")
            path.chmod(0o600)
            _load_env(path)
            self.assertEqual(os.environ["ALPACA_PAPER_API_SECRET"], "$(not-a-command)")

    def test_reset_run_command_requires_explicit_confirmation_argument(self) -> None:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        add_paper_parser(subparsers)
        args = parser.parse_args(
            [
                "paper", "reset-run", "--confirmation",
                "REBASELINE-PAPER-RUN-AT-CLEAN-500",
            ]
        )
        self.assertEqual(args.paper_command, "reset-run")
        self.assertEqual(
            args.confirmation, "REBASELINE-PAPER-RUN-AT-CLEAN-500"
        )


if __name__ == "__main__":
    unittest.main()
