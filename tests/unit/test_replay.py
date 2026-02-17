import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "display_protocol"))

from smartscreen_display.replay import ReplayRunner


class ReplayTests(unittest.TestCase):
    def test_replay_report_detects_core_commands(self):
        runner = ReplayRunner()
        transcript = ROOT / "tests" / "transcripts" / "rev_a_handshake_frame.jsonl"
        report = runner.run(transcript, strict=True)

        self.assertEqual(report.hello_count, 1)
        self.assertEqual(report.orientation_count, 1)
        self.assertEqual(report.window_count, 1)
        self.assertEqual(report.errors, [])


if __name__ == "__main__":
    unittest.main()
