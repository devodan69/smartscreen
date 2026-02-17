import sys
import unittest
from pathlib import Path

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "renderer"))
sys.path.insert(0, str(ROOT / "packages" / "display_protocol"))

from smartscreen_renderer.rgb565 import build_test_pattern, image_to_rgb565_le, rgb888_bytes_to_rgb565_le


class RGB565Tests(unittest.TestCase):
    def test_single_red_pixel(self):
        data = bytes([255, 0, 0])
        rgb565 = rgb888_bytes_to_rgb565_le(data)
        self.assertEqual(rgb565, bytes([0x00, 0xF8]))

    def test_image_conversion_size(self):
        if Image is None:
            self.skipTest("Pillow not installed")
        img = Image.new("RGB", (10, 10), (10, 20, 30))
        out = image_to_rgb565_le(img)
        self.assertEqual(len(out), 200)

    def test_pattern_dimensions(self):
        if Image is None:
            self.skipTest("Pillow not installed")
        img = build_test_pattern("quadrants", width=800, height=480)
        self.assertEqual(img.size, (800, 480))


if __name__ == "__main__":
    unittest.main()
