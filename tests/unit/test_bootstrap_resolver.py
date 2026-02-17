import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "installers" / "bootstrap"))

from smartscreen_bootstrap.resolver import Asset, resolve_target, select_asset, select_installer_asset


class BootstrapResolverTests(unittest.TestCase):
    def test_resolve_target(self):
        target = resolve_target("Windows", "AMD64")
        self.assertEqual(target.os_name, "windows")
        self.assertEqual(target.arch, "x64")

    def test_select_asset(self):
        assets = [
            Asset(name="smartscreen-v1.0.0-windows-x64.exe", url="https://example/windows.exe"),
            Asset(name="smartscreen-v1.0.0-macos-arm64.dmg", url="https://example/macos.dmg"),
        ]
        target = resolve_target("Windows", "AMD64")
        selected = select_asset(assets, target)
        self.assertIn("windows", selected.name)

    def test_select_installer_asset_prefers_installer(self):
        assets = [
            Asset(name="SmartScreen-windows-x64.exe", url="https://example/app.exe"),
            Asset(name="SmartScreenInstaller-windows-x64.exe", url="https://example/installer.exe"),
        ]
        target = resolve_target("Windows", "AMD64")
        selected = select_installer_asset(assets, target)
        self.assertIn("installer", selected.name.lower())


if __name__ == "__main__":
    unittest.main()
