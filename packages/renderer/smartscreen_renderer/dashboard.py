"""Dashboard image composer for 800x480 display output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from .models import FrameBuffer, ThemeConfig
from .rgb565 import image_to_rgb565_le
from .themes import get_theme


@dataclass(frozen=True)
class DashboardData:
    cpu_percent: float
    cpu_temp_c: float | None
    gpu_percent: float | None
    gpu_temp_c: float | None
    ram_used_gb: float
    ram_total_gb: float
    disk_used_gb: float
    disk_total_gb: float
    net_up_mbps: float
    net_down_mbps: float
    timestamp: datetime


class DashboardRenderer:
    """Draws modern dashboard cards and converts frame to RGB565 LE."""

    def __init__(self, width: int = 800, height: int = 480) -> None:
        self.width = width
        self.height = height

    def render(self, snapshot: DashboardData, theme_name: str | None = None) -> FrameBuffer:
        image = self.render_image(snapshot, theme_name)
        return FrameBuffer(width=self.width, height=self.height, pixel_format="RGB565_LE", bytes=image_to_rgb565_le(image))

    def render_image(self, snapshot: DashboardData, theme_name: str | None = None) -> Image.Image:
        theme = get_theme(theme_name)
        image = Image.new("RGB", (self.width, self.height), theme.background_start)
        draw = ImageDraw.Draw(image)

        self._paint_gradient(image, theme)
        self._draw_header(draw, theme)
        self._draw_cards(draw, theme, snapshot)
        self._draw_footer(draw, theme, snapshot)
        return image

    def preview_data_url(self, snapshot: DashboardData, theme_name: str | None = None) -> str:
        image = self.render_image(snapshot, theme_name)
        buf = BytesIO()
        image.save(buf, format="PNG")
        import base64

        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"

    def _font(self, size: int, mono: bool = False):
        preferred = "JetBrainsMono-Regular.ttf" if mono else "SpaceGrotesk-Regular.ttf"
        try:
            return ImageFont.truetype(preferred, size)
        except Exception:
            try:
                return ImageFont.truetype("Arial.ttf", size)
            except Exception:
                return ImageFont.load_default()

    def _paint_gradient(self, image: Image.Image, theme: ThemeConfig) -> None:
        top = tuple(int(theme.background_start[i : i + 2], 16) for i in (1, 3, 5))
        bottom = tuple(int(theme.background_end[i : i + 2], 16) for i in (1, 3, 5))
        pix = image.load()
        for y in range(self.height):
            t = y / max(self.height - 1, 1)
            r = int(top[0] * (1 - t) + bottom[0] * t)
            g = int(top[1] * (1 - t) + bottom[1] * t)
            b = int(top[2] * (1 - t) + bottom[2] * t)
            for x in range(self.width):
                pix[x, y] = (r, g, b)

    def _draw_header(self, draw: ImageDraw.ImageDraw, theme: ThemeConfig) -> None:
        title_font = self._font(36)
        sub_font = self._font(18, mono=True)
        draw.text((28, 18), "SMARTSCREEN", font=title_font, fill=theme.text_primary)
        draw.text((30, 62), "Live Hardware Dashboard", font=sub_font, fill=theme.text_secondary)

        accent = tuple(int(theme.accent[i : i + 2], 16) for i in (1, 3, 5))
        draw.rounded_rectangle((620, 24, 775, 68), radius=14, outline=accent, width=2)
        draw.text((640, 38), "800x480", font=self._font(18, mono=True), fill=theme.text_primary)

    def _draw_cards(self, draw: ImageDraw.ImageDraw, theme: ThemeConfig, s: DashboardData) -> None:
        card_color = tuple(int(theme.card_bg[i : i + 2], 16) for i in (1, 3, 5))
        primary = tuple(int(theme.text_primary[i : i + 2], 16) for i in (1, 3, 5))
        secondary = tuple(int(theme.text_secondary[i : i + 2], 16) for i in (1, 3, 5))
        accent = tuple(int(theme.accent[i : i + 2], 16) for i in (1, 3, 5))

        cards = [
            ((24, 98, 255, 230), "CPU", f"{s.cpu_percent:05.1f}%", f"Temp {self._fmt_temp(s.cpu_temp_c)}"),
            ((274, 98, 525, 230), "GPU", self._fmt_opt_percent(s.gpu_percent), f"Temp {self._fmt_temp(s.gpu_temp_c)}"),
            ((544, 98, 776, 230), "RAM", f"{s.ram_used_gb:04.1f}/{s.ram_total_gb:04.1f} GB", "Memory"),
            ((24, 248, 388, 392), "NET", f"↑ {s.net_up_mbps:05.2f} MB/s", f"↓ {s.net_down_mbps:05.2f} MB/s"),
            ((412, 248, 776, 392), "DISK", f"{s.disk_used_gb:05.1f}/{s.disk_total_gb:05.1f} GB", "Storage"),
        ]

        for (x0, y0, x1, y1), title, value, subtitle in cards:
            draw.rounded_rectangle((x0, y0, x1, y1), radius=18, fill=card_color)
            draw.text((x0 + 18, y0 + 12), title, font=self._font(20, mono=True), fill=secondary)
            draw.text((x0 + 18, y0 + 56), value, font=self._font(30, mono=True), fill=primary)
            draw.text((x0 + 18, y0 + 98), subtitle, font=self._font(17), fill=secondary)
            draw.rounded_rectangle((x0 + 16, y1 - 16, x1 - 16, y1 - 10), radius=3, fill=accent)

    def _draw_footer(self, draw: ImageDraw.ImageDraw, theme: ThemeConfig, s: DashboardData) -> None:
        primary = tuple(int(theme.text_primary[i : i + 2], 16) for i in (1, 3, 5))
        secondary = tuple(int(theme.text_secondary[i : i + 2], 16) for i in (1, 3, 5))

        draw.text((26, 430), s.timestamp.strftime("%Y-%m-%d %H:%M:%S"), font=self._font(16, mono=True), fill=primary)
        draw.text((560, 430), "LOCAL MODE", font=self._font(16, mono=True), fill=secondary)

    @staticmethod
    def _fmt_temp(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:04.1f}°C"

    @staticmethod
    def _fmt_opt_percent(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:05.1f}%"
