"""CLI entrypoints for SmartScreen desktop and diagnostics."""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime

from smartscreen_core import StreamController, load_config
from smartscreen_display import DisplayTransport
from smartscreen_renderer import build_test_pattern, image_to_rgb565_le


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def cmd_run(_args: argparse.Namespace) -> int:
    from .app import run_gui

    return run_gui()


def cmd_list_devices(_args: argparse.Namespace) -> int:
    devices = DisplayTransport.discover()
    _print_json(
        [
            {
                "device": d.device,
                "description": d.description,
                "hwid": d.hwid,
                "vid": d.vid,
                "pid": d.pid,
                "compatible": d.vid == 0x1A86 and d.pid == 0x5722,
            }
            for d in devices
        ]
    )
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    cfg = load_config()
    devices = DisplayTransport.discover()

    _print_json(
        {
            "timestamp": datetime.now().isoformat(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "config": {
                "device_auto_connect": cfg.device.auto_connect,
                "port_override": cfg.device.port_override,
                "stream_poll_ms": cfg.stream.poll_ms,
                "stream_mode": cfg.stream.mode,
                "dashboard_theme": cfg.ui.dashboard_theme,
                "launch_at_login": cfg.startup.launch_at_login,
                "updates_manual_only": cfg.updates.manual_only,
            },
            "devices": [
                {
                    "device": d.device,
                    "description": d.description,
                    "vid": d.vid,
                    "pid": d.pid,
                    "compatible": d.vid == 0x1A86 and d.pid == 0x5722,
                }
                for d in devices
            ],
        }
    )
    return 0


def cmd_send_test_pattern(args: argparse.Namespace) -> int:
    cfg = load_config()
    controller = StreamController(
        width=800,
        height=480,
        mode="full",
        poll_ms=cfg.stream.poll_ms,
        port_override=(args.port or cfg.device.port_override),
    )

    image = build_test_pattern(args.pattern, width=800, height=480)
    frame = image_to_rgb565_le(image)

    hello = controller.connect()
    stats = controller.send(frame)
    controller.disconnect()

    _print_json(
        {
            "success": True,
            "pattern": args.pattern,
            "hello": {
                "success": hello.success,
                "sub_revision": hello.sub_revision,
                "raw_response_hex": hello.raw_response.hex().upper(),
            },
            "stats": {
                "bytes_sent": stats.bytes_sent,
                "packets_sent": stats.packets_sent,
                "duration_s": stats.duration_s,
                "mode": stats.mode,
            },
        }
    )
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    cfg = load_config()
    controller = StreamController(
        width=800,
        height=480,
        mode=cfg.stream.mode,
        poll_ms=cfg.stream.poll_ms,
        port_override=(args.port or cfg.device.port_override),
    )

    controller.connect()
    patterns = ["checkerboard", "quadrants", "h-gradient", "v-gradient"]
    idx = 0
    frames = 0
    bytes_sent = 0
    start = time.perf_counter()
    deadline = start + args.seconds

    while time.perf_counter() < deadline:
        name = patterns[idx % len(patterns)]
        idx += 1
        img = build_test_pattern(name, width=800, height=480)
        frame = image_to_rgb565_le(img)
        stats = controller.send(frame)
        frames += 1
        bytes_sent += stats.bytes_sent

    elapsed = max(time.perf_counter() - start, 1e-9)
    status = controller.status
    controller.disconnect()

    _print_json(
        {
            "seconds": args.seconds,
            "frames": frames,
            "fps": frames / elapsed,
            "bytes_sent": bytes_sent,
            "throughput_bps": status.throughput_bps,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smartscreen", description="SmartScreen desktop app and tools")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run desktop app")
    run_cmd.set_defaults(func=cmd_run)

    doctor_cmd = sub.add_parser("doctor", help="Print diagnostics and detected devices")
    doctor_cmd.set_defaults(func=cmd_doctor)

    list_cmd = sub.add_parser("list-devices", help="List serial devices")
    list_cmd.set_defaults(func=cmd_list_devices)

    pat_cmd = sub.add_parser("send-test-pattern", help="Send deterministic pattern to display")
    pat_cmd.add_argument("--pattern", default="quadrants", choices=[
        "black",
        "white",
        "red",
        "green",
        "blue",
        "quadrants",
        "h-gradient",
        "v-gradient",
        "checkerboard",
    ])
    pat_cmd.add_argument("--port", default=None, help="Optional explicit serial port override")
    pat_cmd.set_defaults(func=cmd_send_test_pattern)

    bench_cmd = sub.add_parser("benchmark", help="Run streaming benchmark")
    bench_cmd.add_argument("--seconds", type=int, default=30)
    bench_cmd.add_argument("--port", default=None, help="Optional explicit serial port override")
    bench_cmd.set_defaults(func=cmd_benchmark)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
