"""Runtime performance budgeting and adaptive tuning hints."""

from __future__ import annotations

from dataclasses import dataclass

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


@dataclass(frozen=True)
class PerformanceTargets:
    cpu_percent_max: float = 8.0
    rss_mb_max: float = 300.0
    fps_min: float = 5.0
    fps_max: float = 10.0


@dataclass(frozen=True)
class BudgetStatus:
    cpu_percent: float
    rss_mb: float
    fps: float
    overloaded: bool
    warning: str | None
    recommended_poll_ms: int
    recommended_mode: str


class PerformanceController:
    def __init__(self, targets: PerformanceTargets | None = None) -> None:
        self.targets = targets or PerformanceTargets()
        self._process = psutil.Process() if psutil is not None else None
        if self._process is not None:
            # Prime non-blocking CPU measurement.
            self._process.cpu_percent(interval=None)

    def sample(self, fps: float, poll_ms: int, current_mode: str) -> BudgetStatus:
        if self._process is None:
            cpu = 0.0
            rss_mb = 0.0
        else:
            cpu = float(self._process.cpu_percent(interval=None))
            rss_mb = float(self._process.memory_info().rss) / (1024 * 1024)
        overloaded = cpu > self.targets.cpu_percent_max or rss_mb > self.targets.rss_mb_max

        warning = None
        mode = current_mode
        rec_poll = poll_ms

        if overloaded:
            warning = "resource_overload"
            mode = "adaptive"
            rec_poll = min(2000, int(poll_ms * 1.25) + 25)
        elif fps < self.targets.fps_min:
            warning = "below_fps_target"
            rec_poll = max(200, poll_ms - 50)
        elif fps > self.targets.fps_max:
            warning = "above_fps_target"
            rec_poll = min(2000, poll_ms + 50)

        return BudgetStatus(
            cpu_percent=cpu,
            rss_mb=rss_mb,
            fps=float(fps),
            overloaded=overloaded,
            warning=warning,
            recommended_poll_ms=rec_poll,
            recommended_mode=mode,
        )
