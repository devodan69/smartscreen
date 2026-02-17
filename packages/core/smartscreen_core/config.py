"""Persistent app settings schema and load/save helpers."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class DeviceConfig:
    auto_connect: bool = True
    port_override: str | None = None


@dataclass
class DisplayConfig:
    brightness: int = 80


@dataclass
class StreamConfig:
    poll_ms: int = 500
    mode: str = "adaptive"


@dataclass
class UiConfig:
    theme: str = "auto"
    dashboard_theme: str = "Neon Slate"


@dataclass
class StartupConfig:
    launch_at_login: bool = False


@dataclass
class UpdatesConfig:
    manual_only: bool = True


@dataclass
class AppConfig:
    device: DeviceConfig
    display: DisplayConfig
    stream: StreamConfig
    ui: UiConfig
    startup: StartupConfig
    updates: UpdatesConfig


DEFAULT_CONFIG = AppConfig(
    device=DeviceConfig(),
    display=DisplayConfig(),
    stream=StreamConfig(),
    ui=UiConfig(),
    startup=StartupConfig(),
    updates=UpdatesConfig(),
)


def config_path() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "SmartScreen" / "config.json"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "SmartScreen" / "config.json"
    return Path.home() / ".config" / "smartscreen" / "config.json"


def _merge(dataclass_type, raw: dict[str, Any]):
    defaults = dataclass_type()  # type: ignore[misc]
    for k, v in raw.items():
        if hasattr(defaults, k):
            setattr(defaults, k, v)
    return defaults


def load_config(path: Path | None = None) -> AppConfig:
    path = path or config_path()
    if not path.exists():
        return DEFAULT_CONFIG

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_CONFIG

    return AppConfig(
        device=_merge(DeviceConfig, raw.get("device", {})),
        display=_merge(DisplayConfig, raw.get("display", {})),
        stream=_merge(StreamConfig, raw.get("stream", {})),
        ui=_merge(UiConfig, raw.get("ui", {})),
        startup=_merge(StartupConfig, raw.get("startup", {})),
        updates=_merge(UpdatesConfig, raw.get("updates", {})),
    )


def save_config(cfg: AppConfig, path: Path | None = None) -> Path:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg), indent=2, sort_keys=True), encoding="utf-8")
    return path
