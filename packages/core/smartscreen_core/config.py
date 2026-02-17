"""Persistent app settings schema and load/save helpers."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONFIG_VERSION = 2
ONBOARDING_VERSION = 1


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
    reduced_motion: bool = False


@dataclass
class StartupConfig:
    launch_at_login: bool = False


@dataclass
class UpdatesConfig:
    manual_only: bool = True
    channel: str = "stable"
    last_check_utc: str | None = None
    etag: str | None = None


@dataclass
class OnboardingConfig:
    completed: bool = False
    version: int = ONBOARDING_VERSION
    last_device: str | None = None


@dataclass
class DiagnosticsConfig:
    keep_log_files: int = 7
    max_bundle_mb: int = 20


@dataclass
class PerformanceConfig:
    cpu_percent_max: float = 8.0
    rss_mb_max: float = 300.0
    fps_min: float = 5.0
    fps_max: float = 10.0


@dataclass
class AppConfig:
    config_version: int = CONFIG_VERSION
    device: DeviceConfig = field(default_factory=DeviceConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    stream: StreamConfig = field(default_factory=StreamConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    startup: StartupConfig = field(default_factory=StartupConfig)
    updates: UpdatesConfig = field(default_factory=UpdatesConfig)
    onboarding: OnboardingConfig = field(default_factory=OnboardingConfig)
    diagnostics: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)


DEFAULT_CONFIG = AppConfig()


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


def _normalize_updates(cfg: AppConfig) -> None:
    if cfg.updates.channel not in ("stable", "beta"):
        cfg.updates.channel = "stable"


def _normalize_stream(cfg: AppConfig) -> None:
    cfg.stream.poll_ms = max(200, min(2000, int(cfg.stream.poll_ms)))
    if cfg.stream.mode not in ("adaptive", "full"):
        cfg.stream.mode = "adaptive"


def _normalize_performance(cfg: AppConfig) -> None:
    cfg.performance.cpu_percent_max = float(max(1.0, cfg.performance.cpu_percent_max))
    cfg.performance.rss_mb_max = float(max(64.0, cfg.performance.rss_mb_max))
    cfg.performance.fps_min = float(max(1.0, cfg.performance.fps_min))
    cfg.performance.fps_max = float(max(cfg.performance.fps_min, cfg.performance.fps_max))


def _migrate(raw: dict[str, Any]) -> dict[str, Any]:
    version = int(raw.get("config_version", 1))
    data = dict(raw)

    if version < 2:
        # v2 introduces onboarding/diagnostics/performance/updates channel metadata.
        data.setdefault("onboarding", {})
        data.setdefault("diagnostics", {})
        data.setdefault("performance", {})
        updates = dict(data.get("updates", {}) or {})
        updates.setdefault("channel", "stable")
        updates.setdefault("last_check_utc", None)
        updates.setdefault("etag", None)
        data["updates"] = updates
        data["config_version"] = 2

    return data


def load_config(path: Path | None = None) -> AppConfig:
    path = path or config_path()
    if not path.exists():
        return AppConfig()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return AppConfig()

    data = _migrate(raw)
    cfg = AppConfig(
        config_version=int(data.get("config_version", CONFIG_VERSION)),
        device=_merge(DeviceConfig, data.get("device", {})),
        display=_merge(DisplayConfig, data.get("display", {})),
        stream=_merge(StreamConfig, data.get("stream", {})),
        ui=_merge(UiConfig, data.get("ui", {})),
        startup=_merge(StartupConfig, data.get("startup", {})),
        updates=_merge(UpdatesConfig, data.get("updates", {})),
        onboarding=_merge(OnboardingConfig, data.get("onboarding", {})),
        diagnostics=_merge(DiagnosticsConfig, data.get("diagnostics", {})),
        performance=_merge(PerformanceConfig, data.get("performance", {})),
    )

    _normalize_updates(cfg)
    _normalize_stream(cfg)
    _normalize_performance(cfg)
    return cfg


def save_config(cfg: AppConfig, path: Path | None = None) -> Path:
    cfg.config_version = CONFIG_VERSION
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg), indent=2, sort_keys=True), encoding="utf-8")
    return path


def touch_update_check(cfg: AppConfig) -> None:
    cfg.updates.last_check_utc = datetime.now(timezone.utc).isoformat()
