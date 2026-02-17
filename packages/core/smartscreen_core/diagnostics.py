"""Diagnostics export helpers for local support bundles."""

from __future__ import annotations

import json
import os
import platform
import re
import tempfile
import zipfile
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smartscreen_display import DisplayTransport

from .config import AppConfig, config_path
from .logging_setup import log_dir


_SECRET_RE = re.compile(r"(token|secret|password|apikey|api_key|auth)", re.IGNORECASE)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    return value


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if _SECRET_RE.search(k):
                out[k] = "***REDACTED***"
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def build_doctor_payload(cfg: AppConfig) -> dict[str, Any]:
    devices = DisplayTransport.discover()
    return {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "config": redact(asdict(cfg)),
        "devices": [
            {
                "device": d.device,
                "description": d.description,
                "vid": d.vid,
                "pid": d.pid,
                "compatible": d.vid == 0x1A86 and d.pid == 0x5722,
            }
            for d in devices
        ],
    }


class DiagnosticsExporter:
    def __init__(self, app_name: str = "SmartScreen") -> None:
        self.app_name = app_name

    def bundle(
        self,
        cfg: AppConfig,
        doctor_payload: dict[str, Any],
        recent_transport_events: list[dict[str, Any]] | None = None,
        output_dir: Path | None = None,
    ) -> Path:
        output_base = output_dir or Path(tempfile.gettempdir())
        output_base.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        zip_path = output_base / f"smartscreen-diagnostics-{stamp}.zip"

        config_file = config_path()
        logs = sorted(log_dir().glob("*.log*"))

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "app": self.app_name,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "host": platform.platform(),
                "python": platform.python_version(),
                "config_path": str(config_file),
                "log_dir": str(log_dir()),
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
            zf.writestr("doctor.json", json.dumps(redact(doctor_payload), indent=2, sort_keys=True, default=_jsonable))
            zf.writestr("config.redacted.json", json.dumps(redact(asdict(cfg)), indent=2, sort_keys=True))
            zf.writestr(
                "transport_events.json",
                json.dumps(redact(recent_transport_events or []), indent=2, sort_keys=True, default=_jsonable),
            )

            for item in logs:
                zf.write(item, arcname=f"logs/{item.name}")

            fault_file = log_dir() / "fault.log"
            if fault_file.exists():
                zf.write(fault_file, arcname="logs/fault.log")

        return zip_path
