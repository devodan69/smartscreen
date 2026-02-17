"""System telemetry providers for SmartScreen."""

from .models import ClockMetrics, CpuMetrics, DiskMetrics, GpuMetrics, MemoryMetrics, MetricSnapshot, NetworkMetrics
try:  # pragma: no cover - optional at import time for minimal test environments
    from .provider import TelemetryProvider
except Exception:  # pragma: no cover
    TelemetryProvider = None  # type: ignore[assignment]

__all__ = [
    "ClockMetrics",
    "CpuMetrics",
    "DiskMetrics",
    "GpuMetrics",
    "MemoryMetrics",
    "MetricSnapshot",
    "NetworkMetrics",
]

if TelemetryProvider is not None:
    __all__.append("TelemetryProvider")
