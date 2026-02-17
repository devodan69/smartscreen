"""Replay/analysis utilities for captured protocol transcripts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .rev_a import RevACommand


_HEX_CLEAN = re.compile(r"[^0-9a-fA-F]")


@dataclass(frozen=True)
class ReplayEvent:
    line: int
    direction: str
    payload: bytes


@dataclass
class ReplayReport:
    total_events: int = 0
    host_to_device_events: int = 0
    device_to_host_events: int = 0
    hello_count: int = 0
    orientation_count: int = 0
    window_count: int = 0
    payload_packets: int = 0
    raw_bytes_total: int = 0
    command_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class ReplayRunner:
    @staticmethod
    def _decode_hex(value: str) -> bytes:
        cleaned = _HEX_CLEAN.sub("", value)
        if len(cleaned) % 2 == 1:
            cleaned = cleaned[:-1]
        if not cleaned:
            return b""
        return bytes.fromhex(cleaned)

    def _parse_line(self, line_no: int, line: str) -> ReplayEvent | None:
        stripped = line.strip()
        if not stripped:
            return None
        obj = json.loads(stripped)
        direction = obj.get("dir") or obj.get("direction") or "unknown"
        hex_value = obj.get("payload_hex") or obj.get("hex") or obj.get("hex_preview") or ""
        return ReplayEvent(line=line_no, direction=direction, payload=self._decode_hex(str(hex_value)))

    def parse(self, transcript_path: Path) -> list[ReplayEvent]:
        events: list[ReplayEvent] = []
        for idx, line in enumerate(transcript_path.read_text(encoding="utf-8").splitlines(), start=1):
            event = self._parse_line(idx, line)
            if event is not None:
                events.append(event)
        return events

    def run(self, transcript_path: Path, strict: bool = True) -> ReplayReport:
        events = self.parse(transcript_path)
        report = ReplayReport(total_events=len(events))

        for event in events:
            if event.direction == "host_to_device":
                report.host_to_device_events += 1
            elif event.direction == "device_to_host":
                report.device_to_host_events += 1

            payload = event.payload
            report.raw_bytes_total += len(payload)
            if not payload:
                continue

            if payload == bytes([RevACommand.HELLO] * 6):
                report.hello_count += 1
                report.command_counts["HELLO"] = report.command_counts.get("HELLO", 0) + 1
                continue

            if len(payload) >= 6:
                cmd = payload[5]
                if cmd == int(RevACommand.SET_ORIENTATION):
                    report.orientation_count += 1
                    report.command_counts["SET_ORIENTATION"] = report.command_counts.get("SET_ORIENTATION", 0) + 1
                    continue
                if cmd == int(RevACommand.DISPLAY_BITMAP):
                    report.window_count += 1
                    report.command_counts["DISPLAY_BITMAP"] = report.command_counts.get("DISPLAY_BITMAP", 0) + 1
                    continue

            report.payload_packets += 1

        if strict:
            if report.hello_count < 1:
                report.errors.append("missing_hello")
            if report.orientation_count < 1:
                report.errors.append("missing_orientation")
            if report.window_count < 1:
                report.errors.append("missing_window")

        return report
