import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "display_protocol"))

from smartscreen_display.models import ProtocolState


class ProtocolStateTests(unittest.TestCase):
    def test_recovery_states_present(self):
        self.assertEqual(ProtocolState.CONNECTING.value, "Connecting")
        self.assertEqual(ProtocolState.BACKOFF_WAIT.value, "BackoffWait")
        self.assertEqual(ProtocolState.DEGRADED.value, "Degraded")


if __name__ == "__main__":
    unittest.main()
