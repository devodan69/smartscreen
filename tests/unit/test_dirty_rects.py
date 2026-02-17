import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "renderer"))
sys.path.insert(0, str(ROOT / "packages" / "display_protocol"))

from smartscreen_renderer.rgb565 import compute_dirty_rects


class DirtyRectTests(unittest.TestCase):
    def test_detect_change(self):
        width, height = 8, 8
        prev = bytes([0] * (width * height * 2))
        curr = bytearray(prev)
        curr[10:20] = b"\xAA" * 10
        rects = compute_dirty_rects(prev, bytes(curr), width, height, tile=4)
        self.assertGreaterEqual(len(rects), 1)
        self.assertGreater(rects[0].w, 0)
        self.assertGreater(rects[0].h, 0)

    def test_no_change(self):
        width, height = 8, 8
        frame = bytes([1] * (width * height * 2))
        rects = compute_dirty_rects(frame, frame, width, height)
        self.assertEqual(rects, [])


if __name__ == "__main__":
    unittest.main()
