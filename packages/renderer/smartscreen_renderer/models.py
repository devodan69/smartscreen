"""Typed renderer models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeConfig:
    name: str
    background_start: str
    background_end: str
    card_bg: str
    accent: str
    accent_alt: str
    text_primary: str
    text_secondary: str


@dataclass(frozen=True)
class FrameBuffer:
    width: int
    height: int
    pixel_format: str
    bytes: bytes
