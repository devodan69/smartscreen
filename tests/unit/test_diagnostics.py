import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "core"))
sys.path.insert(0, str(ROOT / "packages" / "display_protocol"))

from smartscreen_core.config import load_config
from smartscreen_core.diagnostics import DiagnosticsExporter, build_doctor_payload


class DiagnosticsTests(unittest.TestCase):
    def test_bundle_exports_zip(self):
        cfg = load_config(Path("/tmp/nonexistent-config.json"))
        doctor = build_doctor_payload(cfg)
        exporter = DiagnosticsExporter()

        with tempfile.TemporaryDirectory() as tmp:
            bundle = exporter.bundle(cfg=cfg, doctor_payload=doctor, output_dir=Path(tmp))
            self.assertTrue(bundle.exists())

            with zipfile.ZipFile(bundle, "r") as zf:
                names = set(zf.namelist())
                self.assertIn("manifest.json", names)
                self.assertIn("doctor.json", names)
                self.assertIn("config.redacted.json", names)


if __name__ == "__main__":
    unittest.main()
