"""Serial transport abstraction for USB display communication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import SerialDevice

try:
    import serial  # type: ignore
    from serial.tools import list_ports  # type: ignore
except Exception:  # pragma: no cover
    serial = None
    list_ports = None


@dataclass
class SerialConfig:
    port: str
    baud: int = 115200
    timeout_ms: int = 500
    rtscts: bool = True


class DisplayTransport:
    """Thin wrapper over pyserial with deterministic settings for this hardware."""

    def __init__(self) -> None:
        self._serial: Any | None = None
        self.config: SerialConfig | None = None

    @property
    def is_open(self) -> bool:
        return bool(self._serial and self._serial.is_open)

    def open(self, port: str, baud: int = 115200, rtscts: bool = True, timeout_ms: int = 500) -> None:
        if serial is None:
            raise RuntimeError("pyserial is required")
        if self.is_open:
            return
        self.config = SerialConfig(port=port, baud=baud, timeout_ms=timeout_ms, rtscts=rtscts)
        self._serial = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=max(timeout_ms, 1) / 1000,
            write_timeout=max(timeout_ms, 1) / 1000,
            rtscts=rtscts,
        )

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def write(self, payload: bytes) -> int:
        if not self.is_open:
            raise RuntimeError("Serial port is not open")
        return int(self._serial.write(payload))

    def read(self, max_len: int, timeout_ms: int | None = None) -> bytes:
        if not self.is_open:
            raise RuntimeError("Serial port is not open")
        if timeout_ms is not None:
            self._serial.timeout = max(timeout_ms, 1) / 1000
        return bytes(self._serial.read(max_len))

    def flush_input(self) -> None:
        if self.is_open:
            self._serial.reset_input_buffer()

    def flush_output(self) -> None:
        if self.is_open:
            self._serial.flush()

    @staticmethod
    def discover() -> list[SerialDevice]:
        if list_ports is None:
            return []
        devices: list[SerialDevice] = []
        for item in list_ports.comports():
            devices.append(
                SerialDevice(
                    device=item.device,
                    description=item.description,
                    hwid=item.hwid,
                    vid=item.vid,
                    pid=item.pid,
                )
            )
        return devices
