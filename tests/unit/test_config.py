import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "core"))

from smartscreen_core.config import AppConfig, load_config, save_config


class ConfigTests(unittest.TestCase):
    def test_load_default_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            cfg = load_config(path)
            self.assertIsInstance(cfg, AppConfig)
            self.assertTrue(cfg.device.auto_connect)

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            cfg = load_config(path)
            cfg.stream.poll_ms = 777
            save_config(cfg, path)
            reloaded = load_config(path)
            self.assertEqual(reloaded.stream.poll_ms, 777)


if __name__ == "__main__":
    unittest.main()
