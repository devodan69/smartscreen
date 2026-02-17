"""Cross-platform telemetry provider with graceful GPU fallbacks."""

from __future__ import annotations

import platform
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import psutil

from .models import ClockMetrics, CpuMetrics, DiskMetrics, GpuMetrics, MemoryMetrics, MetricSnapshot, NetworkMetrics


class _GpuAdapter:
    def poll(self) -> GpuMetrics:
        return GpuMetrics(percent=None, temp_c=None, fan_percent=None, vendor=None)


class _NvmlGpuAdapter(_GpuAdapter):
    def __init__(self) -> None:
        import pynvml  # type: ignore

        self._nvml = pynvml
        pynvml.nvmlInit()

    def poll(self) -> GpuMetrics:
        nvml = self._nvml
        count = nvml.nvmlDeviceGetCount()
        if count < 1:
            return GpuMetrics(percent=None, temp_c=None, fan_percent=None, vendor="nvidia")

        h = nvml.nvmlDeviceGetHandleByIndex(0)
        util = nvml.nvmlDeviceGetUtilizationRates(h)
        temp = nvml.nvmlDeviceGetTemperature(h, nvml.NVML_TEMPERATURE_GPU)
        try:
            fan = float(nvml.nvmlDeviceGetFanSpeed(h))
        except Exception:
            fan = None
        return GpuMetrics(percent=float(util.gpu), temp_c=float(temp), fan_percent=fan, vendor="nvidia")


def _build_gpu_adapter() -> _GpuAdapter:
    try:
        return _NvmlGpuAdapter()
    except Exception:
        return _GpuAdapter()


def _cpu_temp_c() -> float | None:
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        return None
    if not temps:
        return None

    for name in ("coretemp", "cpu_thermal", "k10temp", "acpitz"):
        entries = temps.get(name)
        if entries:
            val = entries[0].current
            return float(val) if val is not None else None

    for _name, entries in temps.items():
        if entries and entries[0].current is not None:
            return float(entries[0].current)
    return None


@dataclass
class _CounterSnapshot:
    ts: float
    net_sent: int
    net_recv: int
    disk_read: int
    disk_write: int


class TelemetryProvider:
    """Single polling provider with normalized units and stable defaults."""

    def __init__(self) -> None:
        now = time.monotonic()
        net = psutil.net_io_counters()
        disk = psutil.disk_io_counters()
        self._prev = _CounterSnapshot(
            ts=now,
            net_sent=(net.bytes_sent if net else 0),
            net_recv=(net.bytes_recv if net else 0),
            disk_read=(disk.read_bytes if disk else 0),
            disk_write=(disk.write_bytes if disk else 0),
        )
        self._gpu = _build_gpu_adapter()
        self._platform = platform.system()

    def poll(self) -> MetricSnapshot:
        now_monotonic = time.monotonic()
        now_utc = datetime.now(timezone.utc)
        elapsed = max(now_monotonic - self._prev.ts, 1e-6)

        cpu_percent = float(psutil.cpu_percent(interval=None))
        freq = psutil.cpu_freq()
        cpu = CpuMetrics(
            percent=cpu_percent,
            temp_c=_cpu_temp_c(),
            freq_mhz=(float(freq.current) if freq else None),
        )

        vm = psutil.virtual_memory()
        memory = MemoryMetrics(
            used_gb=(vm.used / (1024**3)),
            total_gb=(vm.total / (1024**3)),
            percent=float(vm.percent),
        )

        du = psutil.disk_usage("/")
        dio = psutil.disk_io_counters()
        if dio:
            read_mb_s = max(dio.read_bytes - self._prev.disk_read, 0) / elapsed / (1024 * 1024)
            write_mb_s = max(dio.write_bytes - self._prev.disk_write, 0) / elapsed / (1024 * 1024)
            disk_read = dio.read_bytes
            disk_write = dio.write_bytes
        else:
            read_mb_s = 0.0
            write_mb_s = 0.0
            disk_read = self._prev.disk_read
            disk_write = self._prev.disk_write

        disk = DiskMetrics(
            used_gb=du.used / (1024**3),
            total_gb=du.total / (1024**3),
            read_mb_s=read_mb_s,
            write_mb_s=write_mb_s,
        )

        net = psutil.net_io_counters()
        if net:
            up_mb_s = max(net.bytes_sent - self._prev.net_sent, 0) / elapsed / (1024 * 1024)
            down_mb_s = max(net.bytes_recv - self._prev.net_recv, 0) / elapsed / (1024 * 1024)
            net_sent = net.bytes_sent
            net_recv = net.bytes_recv
        else:
            up_mb_s = 0.0
            down_mb_s = 0.0
            net_sent = self._prev.net_sent
            net_recv = self._prev.net_recv

        network = NetworkMetrics(up_mb_s=up_mb_s, down_mb_s=down_mb_s)
        gpu = self._gpu.poll()

        self._prev = _CounterSnapshot(
            ts=now_monotonic,
            net_sent=net_sent,
            net_recv=net_recv,
            disk_read=disk_read,
            disk_write=disk_write,
        )

        return MetricSnapshot(
            cpu=cpu,
            gpu=gpu,
            memory=memory,
            disk=disk,
            network=network,
            clock=ClockMetrics(local_time=now_utc.astimezone()),
            timestamp=now_utc,
        )
