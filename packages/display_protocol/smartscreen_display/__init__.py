"""Display protocol package for USB serial smart screen devices."""

from .models import DirtyRect, HelloResult, ProtocolState, SendStats, SerialDevice
from .replay import ReplayEvent, ReplayReport, ReplayRunner
from .transport import DisplayTransport
from .rev_a import RevAProtocol, auto_select_device

__all__ = [
    "DirtyRect",
    "DisplayTransport",
    "HelloResult",
    "ProtocolState",
    "ReplayEvent",
    "ReplayReport",
    "ReplayRunner",
    "RevAProtocol",
    "SendStats",
    "SerialDevice",
    "auto_select_device",
]
