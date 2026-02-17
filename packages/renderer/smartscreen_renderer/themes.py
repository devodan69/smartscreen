"""Built-in modern dashboard themes."""

from __future__ import annotations

from .models import ThemeConfig

DEFAULT_THEME_NAME = "Neon Slate"

THEMES: dict[str, ThemeConfig] = {
    "Neon Slate": ThemeConfig(
        name="Neon Slate",
        background_start="#0A0F1D",
        background_end="#131B33",
        card_bg="#1A253F",
        accent="#35D9FF",
        accent_alt="#8CFFB5",
        text_primary="#F4F7FF",
        text_secondary="#A9B5D1",
    ),
    "Solar Drift": ThemeConfig(
        name="Solar Drift",
        background_start="#1A140E",
        background_end="#362315",
        card_bg="#473022",
        accent="#FFB347",
        accent_alt="#FFD166",
        text_primary="#FFF7E8",
        text_secondary="#E3CFA8",
    ),
    "Arctic Pulse": ThemeConfig(
        name="Arctic Pulse",
        background_start="#07171F",
        background_end="#123240",
        card_bg="#173F52",
        accent="#59F3FF",
        accent_alt="#86FFD0",
        text_primary="#EFFFFF",
        text_secondary="#B9DFE8",
    ),
}


def list_themes() -> list[str]:
    return sorted(THEMES.keys())


def get_theme(name: str | None) -> ThemeConfig:
    if not name:
        return THEMES[DEFAULT_THEME_NAME]
    return THEMES.get(name, THEMES[DEFAULT_THEME_NAME])
