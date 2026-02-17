"""Core app services for settings, stream control, startup, diagnostics, and updates."""

from .config import AppConfig, load_config, save_config, touch_update_check
from .diagnostics import DiagnosticsExporter, build_doctor_payload
from .performance import BudgetStatus, PerformanceController, PerformanceTargets
from .startup import set_launch_at_login
from .updates import UpdateCheckResult, UpdateService

try:  # Keep import side effects tolerant in minimal test environments.
    from .stream_controller import StreamController, StreamStatus
except Exception:  # pragma: no cover
    StreamController = None  # type: ignore[assignment]
    StreamStatus = None  # type: ignore[assignment]

__all__ = [
    "AppConfig",
    "BudgetStatus",
    "DiagnosticsExporter",
    "PerformanceController",
    "PerformanceTargets",
    "StreamController",
    "StreamStatus",
    "UpdateCheckResult",
    "UpdateService",
    "build_doctor_payload",
    "load_config",
    "save_config",
    "set_launch_at_login",
    "touch_update_check",
]
