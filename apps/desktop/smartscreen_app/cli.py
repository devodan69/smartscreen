"""CLI entrypoints for SmartScreen desktop, diagnostics, replay, and update checks."""

from __future__ import annotations

import argparse
import json
import platform
import time
from dataclasses import asdict
from importlib import metadata
from pathlib import Path

from smartscreen_core import (
    DiagnosticsExporter,
    PerformanceController,
    PerformanceTargets,
    StreamController,
    UpdateService,
    build_doctor_payload,
    load_config,
    save_config,
    touch_update_check,
)
from smartscreen_core.logging_setup import configure_logging
from smartscreen_display import DisplayTransport, ReplayRunner
from smartscreen_renderer import build_test_pattern, image_to_rgb565_le


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def _installed_version() -> str:
    try:
        return metadata.version("smartscreen")
    except Exception:
        return "0.1.0"


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


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config()
    payload = build_doctor_payload(cfg)

    if args.export:
        exporter = DiagnosticsExporter()
        out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else None
        bundle = exporter.bundle(cfg=cfg, doctor_payload=payload, recent_transport_events=[], output_dir=out_dir)
        payload["diagnostics_bundle"] = str(bundle)

    _print_json(payload)
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
    perf = PerformanceController(
        PerformanceTargets(
            cpu_percent_max=cfg.performance.cpu_percent_max,
            rss_mb_max=cfg.performance.rss_mb_max,
            fps_min=cfg.performance.fps_min,
            fps_max=cfg.performance.fps_max,
        )
    )

    controller.connect()
    patterns = ["checkerboard", "quadrants", "h-gradient", "v-gradient"]
    idx = 0
    frames = 0
    bytes_sent = 0
    start = time.perf_counter()
    deadline = start + args.seconds
    samples = []

    while time.perf_counter() < deadline:
        name = patterns[idx % len(patterns)]
        idx += 1
        img = build_test_pattern(name, width=800, height=480)
        frame = image_to_rgb565_le(img)
        stats = controller.send(frame)
        frames += 1
        bytes_sent += stats.bytes_sent

        status = controller.status
        budget = perf.sample(status.fps, controller.poll_ms, controller.mode)
        controller.apply_budget(budget)
        samples.append(asdict(budget))

    elapsed = max(time.perf_counter() - start, 1e-9)
    status = controller.status
    controller.disconnect()

    cpu_max = max((s["cpu_percent"] for s in samples), default=0.0)
    rss_max = max((s["rss_mb"] for s in samples), default=0.0)
    fps_actual = frames / elapsed

    pass_cpu = cpu_max <= cfg.performance.cpu_percent_max
    pass_mem = rss_max <= cfg.performance.rss_mb_max
    pass_fps = cfg.performance.fps_min <= fps_actual <= max(cfg.performance.fps_max * 1.5, cfg.performance.fps_min)

    _print_json(
        {
            "seconds": args.seconds,
            "frames": frames,
            "fps": fps_actual,
            "bytes_sent": bytes_sent,
            "throughput_bps": status.throughput_bps,
            "budget": {
                "targets": {
                    "cpu_percent_max": cfg.performance.cpu_percent_max,
                    "rss_mb_max": cfg.performance.rss_mb_max,
                    "fps_min": cfg.performance.fps_min,
                    "fps_max": cfg.performance.fps_max,
                },
                "max_observed": {
                    "cpu_percent": cpu_max,
                    "rss_mb": rss_max,
                    "fps": fps_actual,
                },
                "pass": bool(pass_cpu and pass_mem and pass_fps),
                "checks": {
                    "cpu": pass_cpu,
                    "memory": pass_mem,
                    "fps": pass_fps,
                },
            },
        }
    )
    return 0


def cmd_updates_check(args: argparse.Namespace) -> int:
    cfg = load_config()
    channel = args.channel or cfg.updates.channel
    service = UpdateService(repo=args.repo)
    current_version = args.current_version

    result = service.check(
        current_version=current_version,
        channel=channel,
        etag=(None if args.ignore_etag else cfg.updates.etag),
    )

    cfg.updates.channel = channel
    cfg.updates.etag = result.etag or cfg.updates.etag
    touch_update_check(cfg)
    save_config(cfg)

    _print_json(asdict(result))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    runner = ReplayRunner()
    report = runner.run(Path(args.transcript), strict=not args.no_strict)
    payload = asdict(report)
    payload["success"] = len(report.errors) == 0
    _print_json(payload)
    return 0 if not report.errors else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smartscreen", description="SmartScreen desktop app and tools")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run desktop app")
    run_cmd.set_defaults(func=cmd_run)

    doctor_cmd = sub.add_parser("doctor", help="Print diagnostics and detected devices")
    doctor_cmd.add_argument("--export", action="store_true", help="Export offline diagnostics bundle")
    doctor_cmd.add_argument("--out-dir", default=None, help="Optional output directory for diagnostics bundle")
    doctor_cmd.set_defaults(func=cmd_doctor)

    list_cmd = sub.add_parser("list-devices", help="List serial devices")
    list_cmd.set_defaults(func=cmd_list_devices)

    pat_cmd = sub.add_parser("send-test-pattern", help="Send deterministic pattern to display")
    pat_cmd.add_argument(
        "--pattern",
        default="quadrants",
        choices=["black", "white", "red", "green", "blue", "quadrants", "h-gradient", "v-gradient", "checkerboard"],
    )
    pat_cmd.add_argument("--port", default=None, help="Optional explicit serial port override")
    pat_cmd.set_defaults(func=cmd_send_test_pattern)

    bench_cmd = sub.add_parser("benchmark", help="Run streaming benchmark")
    bench_cmd.add_argument("--seconds", type=int, default=30)
    bench_cmd.add_argument("--port", default=None, help="Optional explicit serial port override")
    bench_cmd.set_defaults(func=cmd_benchmark)

    updates_cmd = sub.add_parser("updates", help="Manual update checks")
    updates_sub = updates_cmd.add_subparsers(dest="updates_cmd", required=True)
    check_cmd = updates_sub.add_parser("check", help="Check release channel")
    check_cmd.add_argument("--channel", choices=["stable", "beta"], default=None)
    check_cmd.add_argument("--repo", default="devodan69/smartscreen")
    check_cmd.add_argument("--current-version", default=_installed_version())
    check_cmd.add_argument("--ignore-etag", action="store_true")
    check_cmd.set_defaults(func=cmd_updates_check)

    replay_cmd = sub.add_parser("replay", help="Analyze captured serial transcript")
    replay_cmd.add_argument("--transcript", required=True, help="Path to JSONL transcript")
    replay_cmd.add_argument("--no-strict", action="store_true", help="Skip mandatory hello/orientation/window checks")
    replay_cmd.set_defaults(func=cmd_replay)

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging(console=False)
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
