"""Typed telemetry models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CpuMetrics:
    percent: float
    temp_c: float | None
    freq_mhz: float | None


@dataclass(frozen=True)
class GpuMetrics:
    percent: float | None
    temp_c: float | None
    fan_percent: float | None
    vendor: str | None


@dataclass(frozen=True)
class MemoryMetrics:
    used_gb: float
    total_gb: float
    percent: float


@dataclass(frozen=True)
class DiskMetrics:
    used_gb: float
    total_gb: float
    read_mb_s: float
    write_mb_s: float


@dataclass(frozen=True)
class NetworkMetrics:
    up_mb_s: float
    down_mb_s: float


@dataclass(frozen=True)
class ClockMetrics:
    local_time: datetime


@dataclass(frozen=True)
class MetricSnapshot:
    cpu: CpuMetrics
    gpu: GpuMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    network: NetworkMetrics
    clock: ClockMetrics
    timestamp: datetime
