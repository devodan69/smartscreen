"""RGB565 conversion and frame diff helpers."""

from __future__ import annotations

from dataclasses import dataclass

try:  # pragma: no cover
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:  # pragma: no cover
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

from smartscreen_display.models import DirtyRect


@dataclass(frozen=True)
class PatternSpec:
    name: str


def rgb888_bytes_to_rgb565_le(rgb: bytes) -> bytes:
    if len(rgb) % 3 != 0:
        raise ValueError("RGB888 data length must be divisible by 3")
    if np is not None:
        arr = np.frombuffer(rgb, dtype=np.uint8).reshape((-1, 3))
        r = arr[:, 0].astype(np.uint16)
        g = arr[:, 1].astype(np.uint16)
        b = arr[:, 2].astype(np.uint16)
        rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        return rgb565.astype("<u2").tobytes()

    out = bytearray(len(rgb) // 3 * 2)
    w = 0
    for i in range(0, len(rgb), 3):
        r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
        value = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        out[w : w + 2] = value.to_bytes(2, "little")
        w += 2
    return bytes(out)


def image_to_rgb565_le(image: Image.Image) -> bytes:
    if Image is None:
        raise RuntimeError("Pillow is required for image conversion")
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    if image.mode == "RGBA":
        image = image.convert("RGB")
    return rgb888_bytes_to_rgb565_le(image.tobytes())


def build_test_pattern(name: str, width: int, height: int) -> Image.Image:
    if Image is None:
        raise RuntimeError("Pillow is required for test pattern rendering")
    img = Image.new("RGB", (width, height), (0, 0, 0))
    px = img.load()

    for y in range(height):
        for x in range(width):
            if name == "black":
                c = (0, 0, 0)
            elif name == "white":
                c = (255, 255, 255)
            elif name == "red":
                c = (255, 0, 0)
            elif name == "green":
                c = (0, 255, 0)
            elif name == "blue":
                c = (0, 0, 255)
            elif name == "quadrants":
                if x < width // 2 and y < height // 2:
                    c = (255, 0, 0)
                elif x >= width // 2 and y < height // 2:
                    c = (0, 255, 0)
                elif x < width // 2 and y >= height // 2:
                    c = (0, 0, 255)
                else:
                    c = (255, 255, 255)
            elif name == "h-gradient":
                v = int(255 * (x / max(width - 1, 1)))
                c = (v, v, v)
            elif name == "v-gradient":
                v = int(255 * (y / max(height - 1, 1)))
                c = (v, v, v)
            elif name == "checkerboard":
                c = (255, 255, 255) if ((x // 24 + y // 24) % 2 == 0) else (0, 0, 0)
            else:
                raise ValueError(f"Unknown pattern: {name}")
            px[x, y] = c
    return img


def compute_dirty_rects(
    previous_frame: bytes,
    current_frame: bytes,
    width: int,
    height: int,
    tile: int = 32,
    max_ratio: float = 0.35,
) -> list[DirtyRect]:
    if len(previous_frame) != len(current_frame):
        raise ValueError("Frame sizes must match")

    changed_tiles: list[tuple[int, int]] = []
    stride = width * 2

    for y in range(0, height, tile):
        for x in range(0, width, tile):
            w = min(tile, width - x)
            h = min(tile, height - y)
            changed = False
            for row in range(h):
                start = (y + row) * stride + x * 2
                end = start + w * 2
                if previous_frame[start:end] != current_frame[start:end]:
                    changed = True
                    break
            if changed:
                changed_tiles.append((x, y))

    if not changed_tiles:
        return []

    changed_pixels = len(changed_tiles) * tile * tile
    if changed_pixels / (width * height) > max_ratio:
        return [DirtyRect(x=0, y=0, w=width, h=height)]

    min_x = min(t[0] for t in changed_tiles)
    min_y = min(t[1] for t in changed_tiles)
    max_x = max(t[0] for t in changed_tiles)
    max_y = max(t[1] for t in changed_tiles)
    rect_w = min(width - min_x, (max_x - min_x) + tile)
    rect_h = min(height - min_y, (max_y - min_y) + tile)
    return [DirtyRect(x=min_x, y=min_y, w=rect_w, h=rect_h)]
