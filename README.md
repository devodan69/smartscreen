# SmartScreen

Modern cross-platform desktop app for USB serial smart displays (`VID:PID 1A86:5722`) with full-screen `800x480` landscape rendering.

## Features

- Windows, macOS, and Linux desktop app (PySide6 + QML)
- Local-only runtime (no telemetry upload)
- Serial protocol implementation for rev-A style display transport
- Adaptive frame updates (full frame + dirty-rect)
- Built-in modern themes and dashboard preview
- Tray/menubar support, launch-at-login toggle
- One bootstrap installer entrypoint scripts

## Project Layout

- `apps/desktop/smartscreen_app`: desktop UI and CLI
- `packages/display_protocol/smartscreen_display`: serial protocol stack
- `packages/telemetry/smartscreen_telemetry`: system metrics providers
- `packages/renderer/smartscreen_renderer`: dashboard composition and RGB565 encoding
- `packages/core/smartscreen_core`: settings and stream controller
- `installers/bootstrap`: cross-platform installer bootstrap

## Quick Start

```bash
cd /Volumes/Projects/usb-smart-screen-app
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
smartscreen run
```

## CLI

```bash
smartscreen run
smartscreen doctor
smartscreen list-devices
smartscreen send-test-pattern --pattern quadrants
smartscreen benchmark --seconds 30
```

## Device Protocol

- Auto-detect serial device `VID=0x1A86`, `PID=0x5722`
- `115200`, `8N1`, `rtscts=true`
- HELLO (`0x45` x 6), orientation (`0x79`), display window (`0xC5`), raw RGB565 LE stream

## Installer Bootstrap

End users should install from release artifacts only (double-click, no terminal):

- Windows: `SmartScreenInstaller-windows-x64.exe`
- macOS: `SmartScreenInstaller-macos-<arch>.dmg`
- Linux: `SmartScreenInstaller-linux-<arch>.AppImage`

Direct app binaries are also published:

- `SmartScreen-windows-<arch>.exe`
- `SmartScreen-macos-<arch>.dmg`
- `SmartScreen-linux-<arch>.AppImage`

The bootstrap logic verifies `checksums.txt` before launching installers.

Developer bootstrap helpers remain available under `installers/bootstrap/` and can be run with:
`smartscreen-installer`

## Tests

```bash
python -m pytest -q
```

## Notes

- v1 targets one device class only (`1A86:5722`).
- Legacy `.pcdate` import is intentionally out-of-scope.
