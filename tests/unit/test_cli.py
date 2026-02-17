import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "desktop"))
sys.path.insert(0, str(ROOT / "packages" / "core"))
sys.path.insert(0, str(ROOT / "packages" / "display_protocol"))
sys.path.insert(0, str(ROOT / "packages" / "renderer"))
sys.path.insert(0, str(ROOT / "packages" / "telemetry"))

from smartscreen_app.cli import build_parser


class CliTests(unittest.TestCase):
    def test_run_command(self):
        parser = build_parser()
        args = parser.parse_args(["run"])
        self.assertEqual(args.command, "run")

    def test_pattern_command(self):
        parser = build_parser()
        args = parser.parse_args(["send-test-pattern", "--pattern", "quadrants"])
        self.assertEqual(args.command, "send-test-pattern")
        self.assertEqual(args.pattern, "quadrants")


if __name__ == "__main__":
    unittest.main()
