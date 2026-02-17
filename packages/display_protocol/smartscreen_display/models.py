"""Typed models for display transport and protocol state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProtocolState(str, Enum):
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    PORT_OPEN = "PortOpen"
    HELLO = "Hello"
    ORIENTATION_SET = "OrientationSet"
    READY = "Ready"
    STREAMING = "Streaming"
    BACKOFF_WAIT = "BackoffWait"
    RECOVERING = "Recovering"
    DEGRADED = "Degraded"


@dataclass(frozen=True)
class SerialDevice:
    device: str
    description: str
    hwid: str
    vid: int | None
    pid: int | None


@dataclass(frozen=True)
class HelloResult:
    success: bool
    raw_response: bytes
    sub_revision: str
    portrait_width: int
    portrait_height: int


@dataclass(frozen=True)
class DirtyRect:
    x: int
    y: int
    w: int
    h: int


@dataclass
class SendStats:
    bytes_sent: int = 0
    packets_sent: int = 0
    errors: int = 0
    retries: int = 0
    duration_s: float = 0.0
    mode: str = "full"
