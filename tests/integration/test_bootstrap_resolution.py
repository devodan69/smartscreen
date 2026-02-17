import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "installers" / "bootstrap"))

from smartscreen_bootstrap.resolver import Asset, resolve_target, select_asset


class BootstrapIntegrationTests(unittest.TestCase):
    def test_multi_asset_selection(self):
        assets = [
            Asset(name="checksums.txt", url="x"),
            Asset(name="smartscreen-v1.2.3-windows-x64.exe", url="x"),
            Asset(name="smartscreen-v1.2.3-macos-arm64.dmg", url="x"),
            Asset(name="smartscreen-v1.2.3-linux-x64.AppImage", url="x"),
        ]
        target = resolve_target("Linux", "x86_64")
        selected = select_asset(assets, target)
        self.assertTrue(selected.name.endswith(".AppImage"))


if __name__ == "__main__":
    unittest.main()
