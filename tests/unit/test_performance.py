import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "core"))

from smartscreen_core.performance import PerformanceController, PerformanceTargets


class PerformanceTests(unittest.TestCase):
    def test_budget_sample_shape(self):
        ctl = PerformanceController(PerformanceTargets(cpu_percent_max=100.0, rss_mb_max=2048.0, fps_min=5.0, fps_max=10.0))
        status = ctl.sample(fps=6.0, poll_ms=500, current_mode="adaptive")
        self.assertIn(status.recommended_mode, ("adaptive", "full"))
        self.assertGreaterEqual(status.recommended_poll_ms, 200)


if __name__ == "__main__":
    unittest.main()
