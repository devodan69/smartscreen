"""Streaming controller with adaptive updates and reconnect handling."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from smartscreen_display import DisplayTransport, RevAProtocol, auto_select_device
from smartscreen_display.models import HelloResult, ProtocolState, SendStats
from smartscreen_renderer.rgb565 import compute_dirty_rects


@dataclass
class StreamStatus:
    connected: bool = False
    port: str | None = None
    state: ProtocolState = ProtocolState.DISCONNECTED
    fps: float = 0.0
    throughput_bps: float = 0.0
    last_error: str | None = None


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

    @property
    def status(self) -> StreamStatus:
        return self._status

    def connect(self) -> HelloResult:
        with self._lock:
            port = self.port_override
            if not port:
                selected = auto_select_device(DisplayTransport.discover())
                if not selected:
                    raise RuntimeError("No compatible display found")
                port = selected.device

            self._transport.open(port=port, baud=115200, rtscts=True, timeout_ms=500)
            self._status.state = ProtocolState.PORT_OPEN
            hello = self._protocol.handshake(timeout_ms=500)
            self._status.connected = True
            self._status.port = port
            self._status.state = ProtocolState.READY
            self._status.last_error = None
            return hello

    def disconnect(self) -> None:
        with self._lock:
            self._transport.close()
            self._status.connected = False
            self._status.state = ProtocolState.DISCONNECTED
            self._previous_frame = None

    def set_brightness(self, percent: int) -> None:
        with self._lock:
            if not self._status.connected:
                return
            self._protocol.set_brightness(percent)

    def send(self, frame: bytes) -> SendStats:
        with self._lock:
            if not self._status.connected:
                self.connect()

            start = time.perf_counter()
            try:
                if self.mode == "adaptive" and self._previous_frame is not None:
                    rects = compute_dirty_rects(self._previous_frame, frame, self.width, self.height, tile=32)
                    if rects and not (len(rects) == 1 and rects[0].w == self.width and rects[0].h == self.height):
                        stats = self._protocol.send_dirty_rects(rects, frame)
                    else:
                        stats = self._protocol.send_frame(frame)
                else:
                    stats = self._protocol.send_frame(frame)
            except Exception as exc:
                self._status.last_error = str(exc)
                self._status.state = ProtocolState.RECOVERING
                self._recover_once()
                stats = self._protocol.send_frame(frame)

            elapsed = max(time.perf_counter() - start, 1e-9)
            fps = 1.0 / elapsed
            bps = stats.bytes_sent / elapsed
            self._ewma_bps = bps if self._ewma_bps == 0 else (0.75 * self._ewma_bps + 0.25 * bps)

            self._status.state = ProtocolState.STREAMING
            self._status.fps = fps
            self._status.throughput_bps = self._ewma_bps
            self._previous_frame = frame
            return stats

    def _recover_once(self) -> None:
        try:
            self.disconnect()
            self.connect()
        except Exception as exc:
            self._status.connected = False
            self._status.state = ProtocolState.RECOVERING
            self._status.last_error = str(exc)
            raise
