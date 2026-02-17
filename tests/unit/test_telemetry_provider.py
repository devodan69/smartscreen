import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "telemetry"))

try:
    from smartscreen_telemetry.provider import TelemetryProvider
except Exception:  # pragma: no cover
    TelemetryProvider = None


class TelemetryProviderTests(unittest.TestCase):
    def test_poll_returns_snapshot(self):
        if TelemetryProvider is None:
            self.skipTest("psutil not installed")
        provider = TelemetryProvider()
        snap = provider.poll()
        self.assertGreaterEqual(snap.cpu.percent, 0.0)
        self.assertGreater(snap.memory.total_gb, 0.0)
        self.assertIsNotNone(snap.clock.local_time)


if __name__ == "__main__":
    unittest.main()
