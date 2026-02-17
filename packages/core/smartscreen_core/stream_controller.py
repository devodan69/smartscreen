"""Streaming controller with adaptive updates, performance hints, and reconnect handling."""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from smartscreen_display import DisplayTransport, RevAProtocol, auto_select_device
from smartscreen_display.models import HelloResult, ProtocolState, SendStats
from smartscreen_renderer.rgb565 import compute_dirty_rects

from .performance import BudgetStatus


@dataclass
class StreamStatus:
    connected: bool = False
    port: str | None = None
    state: ProtocolState = ProtocolState.DISCONNECTED
    fps: float = 0.0
    throughput_bps: float = 0.0
    last_error: str | None = None
    backoff_seconds: float = 0.0
    recovery_attempts: int = 0


class StreamController:
    def __init__(
        self,
        width: int = 800,
        height: int = 480,
        mode: str = "adaptive",
        poll_ms: int = 500,
        port_override: str | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.mode = mode
        self.poll_ms = poll_ms
        self.port_override = port_override

        self._transport = DisplayTransport()
        self._protocol = RevAProtocol(self._transport, width=width, height=height)
        self._status = StreamStatus()
        self._lock = threading.RLock()
        self._previous_frame: bytes | None = None
        self._ewma_bps = 0.0
        self._events: list[dict[str, Any]] = []

        self._max_recover_attempts = 5
        self._backoff_base = 0.25
        self._backoff_cap = 4.0
        self._force_full_frames_remaining = 0

    @property
    def status(self) -> StreamStatus:
        return self._status

    def recent_events(self, limit: int = 200) -> list[dict[str, Any]]:
        return self._events[-limit:]

    def _log_event(self, event: str, **fields: Any) -> None:
        row = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "state": self._status.state.value,
        }
        row.update(fields)
        self._events.append(row)
        if len(self._events) > 1000:
            self._events = self._events[-1000:]

    def connect(self) -> HelloResult:
        with self._lock:
            self._status.state = ProtocolState.CONNECTING
            self._log_event("connect_start")

            port = self.port_override
            if not port:
                selected = auto_select_device(DisplayTransport.discover())
                if not selected:
                    self._status.state = ProtocolState.DISCONNECTED
                    raise RuntimeError("No compatible display found")
                port = selected.device

            self._transport.open(port=port, baud=115200, rtscts=True, timeout_ms=500)
            self._status.state = ProtocolState.PORT_OPEN
            self._status.recovery_attempts = 0
            self._status.backoff_seconds = 0.0

            hello = self._protocol.handshake(timeout_ms=500)
            self._status.connected = True
            self._status.port = port
            self._status.state = ProtocolState.READY
            self._status.last_error = None
            self._log_event("connect_ok", port=port, sub_revision=hello.sub_revision)
            return hello

    def disconnect(self) -> None:
        with self._lock:
            self._transport.close()
            self._status.connected = False
            self._status.state = ProtocolState.DISCONNECTED
            self._previous_frame = None
            self._status.backoff_seconds = 0.0
            self._status.recovery_attempts = 0
            self._log_event("disconnect")

    def set_brightness(self, percent: int) -> None:
        with self._lock:
            if not self._status.connected:
                return
            self._protocol.set_brightness(percent)
            self._log_event("brightness", percent=percent)

    def apply_budget(self, budget: BudgetStatus) -> None:
        with self._lock:
            self.poll_ms = max(200, min(2000, int(budget.recommended_poll_ms)))
            self.mode = budget.recommended_mode
            if budget.overloaded:
                self._status.state = ProtocolState.DEGRADED
                self._force_full_frames_remaining = max(self._force_full_frames_remaining, 2)
                self._protocol.chunk_size = max(self.width * 4, 256)
                self._log_event(
                    "budget_overload",
                    cpu_percent=budget.cpu_percent,
                    rss_mb=budget.rss_mb,
                    recommended_poll_ms=self.poll_ms,
                )
            else:
                self._protocol.chunk_size = self.width * 8

    def send(self, frame: bytes) -> SendStats:
        with self._lock:
            if not self._status.connected:
                self.connect()

            start = time.perf_counter()
            stats = SendStats()
            try:
                stats = self._send_once(frame)
            except Exception as exc:
                self._status.last_error = str(exc)
                self._status.state = ProtocolState.RECOVERING
                self._log_event("send_error", error=str(exc))
                self._recover_with_backoff()
                stats = self._protocol.send_frame(frame)
                stats.retries += 1

            elapsed = max(time.perf_counter() - start, 1e-9)
            fps = 1.0 / elapsed
            bps = stats.bytes_sent / elapsed
            self._ewma_bps = bps if self._ewma_bps == 0 else (0.75 * self._ewma_bps + 0.25 * bps)

            self._status.state = ProtocolState.STREAMING if self._force_full_frames_remaining == 0 else ProtocolState.DEGRADED
            self._status.fps = fps
            self._status.throughput_bps = self._ewma_bps
            self._status.backoff_seconds = 0.0
            self._status.recovery_attempts = 0
            self._previous_frame = frame
            self._log_event(
                "send_ok",
                mode=stats.mode,
                bytes_sent=stats.bytes_sent,
                packets_sent=stats.packets_sent,
                fps=fps,
                throughput_bps=self._ewma_bps,
            )
            return stats

    def _send_once(self, frame: bytes) -> SendStats:
        if self._force_full_frames_remaining > 0:
            self._force_full_frames_remaining -= 1
            return self._protocol.send_frame(frame)

        if self.mode == "adaptive" and self._previous_frame is not None:
            rects = compute_dirty_rects(self._previous_frame, frame, self.width, self.height, tile=32)
            if rects and not (len(rects) == 1 and rects[0].w == self.width and rects[0].h == self.height):
                return self._protocol.send_dirty_rects(rects, frame)
        return self._protocol.send_frame(frame)

    def _recover_with_backoff(self) -> None:
        last_error: Exception | None = None
        for attempt in range(1, self._max_recover_attempts + 1):
            delay = min(self._backoff_cap, self._backoff_base * (2 ** (attempt - 1)))
            jitter = random.uniform(0.0, 0.15)
            wait_for = delay + jitter

            self._status.state = ProtocolState.BACKOFF_WAIT
            self._status.backoff_seconds = wait_for
            self._status.recovery_attempts = attempt
            self._log_event("recover_wait", attempt=attempt, wait_s=wait_for)
            time.sleep(wait_for)

            try:
                self._status.state = ProtocolState.RECOVERING
                self.disconnect()
                self.connect()
                self._status.state = ProtocolState.DEGRADED
                self._force_full_frames_remaining = 3
                self._log_event("recover_ok", attempt=attempt)
                return
            except Exception as exc:
                last_error = exc
                self._status.last_error = str(exc)
                self._log_event("recover_error", attempt=attempt, error=str(exc))

        self._status.connected = False
        self._status.state = ProtocolState.RECOVERING
        raise RuntimeError(f"recover failed after {self._max_recover_attempts} attempts: {last_error}")
