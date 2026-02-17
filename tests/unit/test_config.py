import json
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
            self.assertFalse(cfg.onboarding.completed)
            self.assertEqual(cfg.updates.channel, "stable")

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            cfg = load_config(path)
            cfg.stream.poll_ms = 777
            cfg.onboarding.completed = True
            save_config(cfg, path)
            reloaded = load_config(path)
            self.assertEqual(reloaded.stream.poll_ms, 777)
            self.assertTrue(reloaded.onboarding.completed)

    def test_migrate_v1_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            old = {
                "device": {"auto_connect": True},
                "stream": {"poll_ms": 450},
                "updates": {"manual_only": True},
            }
            path.write_text(json.dumps(old), encoding="utf-8")
            cfg = load_config(path)
            self.assertEqual(cfg.stream.poll_ms, 450)
            self.assertEqual(cfg.updates.channel, "stable")
            self.assertIn(cfg.ui.theme, ("auto", "dark", "light"))


if __name__ == "__main__":
    unittest.main()
