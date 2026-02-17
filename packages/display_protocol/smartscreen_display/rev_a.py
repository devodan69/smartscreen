"""Revision-A serial protocol implementation for VID:PID 1A86:5722 displays."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import IntEnum

from .models import DirtyRect, HelloResult, ProtocolState, SendStats, SerialDevice
from .transport import DisplayTransport


class RevACommand(IntEnum):
    RESET = 0x65
    CLEAR = 0x66
    TO_BLACK = 0x67
    SCREEN_OFF = 0x6C
    SCREEN_ON = 0x6D
    SET_BRIGHTNESS = 0x6E
    HELLO = 0x45
    SET_ORIENTATION = 0x79
    DISPLAY_BITMAP = 0xC5


class RevAOrientation(IntEnum):
    PORTRAIT = 0
    REVERSE_PORTRAIT = 1
    LANDSCAPE = 2
    REVERSE_LANDSCAPE = 3


@dataclass(frozen=True)
class RevASubRevision:
    name: str
    portrait_width: int
    portrait_height: int


SUB_REVISIONS: dict[bytes, RevASubRevision] = {
    b"\x01\x01\x01\x01\x01\x01": RevASubRevision("usbmonitor_3_5", 320, 480),
    b"\x02\x02\x02\x02\x02\x02": RevASubRevision("usbmonitor_5", 480, 800),
    b"\x03\x03\x03\x03\x03\x03": RevASubRevision("usbmonitor_7", 600, 1024),
}
DEFAULT_SUB = RevASubRevision("unknown", 320, 480)


def auto_select_device(devices: list[SerialDevice]) -> SerialDevice | None:
    """Pick first known device by VID/PID or known serial marker."""
    for d in devices:
        if d.vid == 0x1A86 and d.pid == 0x5722:
            return d
    for d in devices:
        if "USB35INCHIPSV2" in (d.hwid or ""):
            return d
    return None


class RevAProtocol:
    """State-aware sender for landscape 800x480 streaming."""

    def __init__(
        self,
        transport: DisplayTransport,
        width: int = 800,
        height: int = 480,
        chunk_size: int | None = None,
    ) -> None:
        self.transport = transport
        self.state = ProtocolState.DISCONNECTED
        self.width = width
        self.height = height
        self.orientation = RevAOrientation.LANDSCAPE
        self.chunk_size = chunk_size or (width * 8)
        self.sub_revision = DEFAULT_SUB

    @staticmethod
    def _pack_command(cmd: RevACommand, x: int, y: int, ex: int, ey: int) -> bytes:
        if min(x, y, ex, ey) < 0:
            raise ValueError("Coordinates must be non-negative")
        return bytes(
            [
                (x >> 2) & 0xFF,
                (((x & 0x03) << 6) + (y >> 4)) & 0xFF,
                (((y & 0x0F) << 4) + (ex >> 6)) & 0xFF,
                (((ex & 0x3F) << 2) + (ey >> 8)) & 0xFF,
                ey & 0xFF,
                int(cmd) & 0xFF,
            ]
        )

    def hello(self, timeout_ms: int = 500) -> HelloResult:
        self.state = ProtocolState.HELLO
        self.transport.write(bytes([RevACommand.HELLO] * 6))
        response = self.transport.read(max_len=6, timeout_ms=timeout_ms)
        self.transport.flush_input()
        self.sub_revision = SUB_REVISIONS.get(response, DEFAULT_SUB)

        # Some legacy devices do not answer HELLO but still accept commands.
        ok = len(response) in (0, 6)
        return HelloResult(
            success=ok,
            raw_response=response,
            sub_revision=self.sub_revision.name,
            portrait_width=self.sub_revision.portrait_width,
            portrait_height=self.sub_revision.portrait_height,
        )

    def set_orientation(self, width: int = 800, height: int = 480, landscape: bool = True) -> None:
        self.state = ProtocolState.ORIENTATION_SET
        orientation = RevAOrientation.LANDSCAPE if landscape else RevAOrientation.PORTRAIT
        payload = bytearray(16)
        payload[:6] = self._pack_command(RevACommand.SET_ORIENTATION, 0, 0, 0, 0)
        payload[6] = int(orientation) + 100
        payload[7] = (width >> 8) & 0xFF
        payload[8] = width & 0xFF
        payload[9] = (height >> 8) & 0xFF
        payload[10] = height & 0xFF

        self.width = width
        self.height = height
        self.orientation = orientation
        self.chunk_size = self.width * 8
        self.transport.write(bytes(payload))
        self.state = ProtocolState.READY

    def handshake(self, timeout_ms: int = 500) -> HelloResult:
        result = self.hello(timeout_ms=timeout_ms)
        if not result.success:
            raise RuntimeError("HELLO handshake failed")
        self.set_orientation(width=self.width, height=self.height, landscape=True)
        self.state = ProtocolState.READY
        return result

    def set_window(self, x0: int, y0: int, x1: int, y1: int) -> int:
        packet = self._pack_command(RevACommand.DISPLAY_BITMAP, x0, y0, x1, y1)
        return self.transport.write(packet)

    def set_brightness(self, level_percent: int) -> int:
        level_percent = max(0, min(100, level_percent))
        level_absolute = int(255 - ((level_percent / 100) * 255))
        packet = self._pack_command(RevACommand.SET_BRIGHTNESS, level_absolute, 0, 0, 0)
        return self.transport.write(packet)

    def send_frame(self, frame_rgb565_le: bytes) -> SendStats:
        expected = self.width * self.height * 2
        if len(frame_rgb565_le) != expected:
            raise ValueError(f"Frame size must be {expected} bytes")

        stats = SendStats(mode="full")
        start = time.perf_counter()

        stats.bytes_sent += self.set_window(0, 0, self.width - 1, self.height - 1)
        stats.packets_sent += 1

        for offset in range(0, len(frame_rgb565_le), self.chunk_size):
            chunk = frame_rgb565_le[offset : offset + self.chunk_size]
            stats.bytes_sent += self.transport.write(chunk)
            stats.packets_sent += 1

        stats.duration_s = time.perf_counter() - start
        self.state = ProtocolState.STREAMING
        return stats

    def send_dirty_rects(self, rects: list[DirtyRect], frame: bytes) -> SendStats:
        if not rects:
            return SendStats(mode="noop")
        stats = SendStats(mode="dirty")
        start = time.perf_counter()

        row_stride = self.width * 2
        for rect in rects:
            stats.bytes_sent += self.set_window(rect.x, rect.y, rect.x + rect.w - 1, rect.y + rect.h - 1)
            stats.packets_sent += 1

            for row in range(rect.y, rect.y + rect.h):
                src_start = row * row_stride + (rect.x * 2)
                src_end = src_start + (rect.w * 2)
                row_bytes = frame[src_start:src_end]
                for offset in range(0, len(row_bytes), self.chunk_size):
                    chunk = row_bytes[offset : offset + self.chunk_size]
                    stats.bytes_sent += self.transport.write(chunk)
                    stats.packets_sent += 1

        stats.duration_s = time.perf_counter() - start
        self.state = ProtocolState.STREAMING
        return stats

    def recover(self, port: str, baud: int = 115200, timeout_ms: int = 500) -> HelloResult:
        self.state = ProtocolState.RECOVERING
        self.transport.close()
        time.sleep(0.2)
        self.transport.open(port=port, baud=baud, timeout_ms=timeout_ms, rtscts=True)
        self.state = ProtocolState.PORT_OPEN
        return self.handshake(timeout_ms=timeout_ms)
