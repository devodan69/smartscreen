"""Renderer package for SmartScreen dashboard composition."""

from .models import FrameBuffer, ThemeConfig
from .rgb565 import (
    build_test_pattern,
    compute_dirty_rects,
    image_to_rgb565_le,
    rgb888_bytes_to_rgb565_le,
)
from .themes import DEFAULT_THEME_NAME, get_theme, list_themes

try:  # pragma: no cover - optional at import time for test environments
    from .dashboard import DashboardRenderer
except Exception:  # pragma: no cover
    DashboardRenderer = None  # type: ignore[assignment]

__all__ = [
    "FrameBuffer",
    "ThemeConfig",
    "DEFAULT_THEME_NAME",
    "build_test_pattern",
    "compute_dirty_rects",
    "get_theme",
    "image_to_rgb565_le",
    "list_themes",
    "rgb888_bytes_to_rgb565_le",
]

if DashboardRenderer is not None:
    __all__.append("DashboardRenderer")
