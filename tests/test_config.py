from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swingbot.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_frozen_config_checksum_is_enforced(self) -> None:
        with TemporaryDirectory() as temporary:
            config = Path(temporary) / "strategy_v1.json"
            config.write_text("{}", encoding="utf-8")
            config.with_suffix(".sha256").write_text("0" * 64 + "  strategy_v1.json\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "checksum mismatch"):
                load_config(config)

    def test_frozen_config_checksum_sidecar_is_required(self) -> None:
        with TemporaryDirectory() as temporary:
            config = Path(temporary) / "strategy_v1.json"
            config.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "sidecar is missing"):
                load_config(config)


if __name__ == "__main__":
    unittest.main()
