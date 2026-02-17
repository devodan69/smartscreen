import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "display_protocol"))

from smartscreen_display.rev_a import RevAProtocol, RevACommand


class FakeTransport:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.writes = []
        self.is_open = True

    def write(self, payload):
        self.writes.append(payload)
        return len(payload)

    def read(self, max_len, timeout_ms=None):
        if self.responses:
            return self.responses.pop(0)
        return b""

    def flush_input(self):
        pass


class RevAProtocolTests(unittest.TestCase):
    def test_pack_command_vector(self):
        pkt = RevAProtocol._pack_command(RevACommand.DISPLAY_BITMAP, 0, 0, 799, 479)
        self.assertEqual(pkt, bytes.fromhex("00000C7DDFC5"))

    def test_handshake_with_hello_response(self):
        t = FakeTransport([b"\x02\x02\x02\x02\x02\x02"])
        p = RevAProtocol(t, width=800, height=480)
        hello = p.handshake()
        self.assertTrue(hello.success)
        self.assertEqual(hello.sub_revision, "usbmonitor_5")
        self.assertEqual(t.writes[0], bytes([0x45] * 6))
        self.assertEqual(len(t.writes[1]), 16)

    def test_send_full_frame(self):
        t = FakeTransport([b""])
        p = RevAProtocol(t, width=4, height=2, chunk_size=4)
        frame = bytes(range(16))
        stats = p.send_frame(frame)
        self.assertEqual(stats.mode, "full")
        self.assertEqual(stats.packets_sent, 5)
        self.assertEqual(t.writes[0], bytes.fromhex("0000000C01C5"))


if __name__ == "__main__":
    unittest.main()
