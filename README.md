# SmartScreen

Modern cross-platform desktop app for USB serial smart displays (`VID:PID 1A86:5722`) with full-screen `800x480` landscape rendering.

## Features

- Windows, macOS, and Linux desktop app (PySide6 + QML)
- First-run onboarding wizard (device scan, permissions hints, startup toggle, test pattern)
- Local-only runtime by default (manual-only update checks)
- Protocol replay regression support from captured JSONL transcripts
- Adaptive streaming with performance budgeting and degraded-mode recovery
- Structured local logging + offline diagnostics bundle export
- Tray/menubar controls and launch-at-login support
- Free-first release workflow with optional signing/notarization per platform

## Project Layout

- `apps/desktop/smartscreen_app`: desktop UI and CLI
- `packages/display_protocol/smartscreen_display`: serial protocol stack + replay analyzer
- `packages/telemetry/smartscreen_telemetry`: system metrics providers
- `packages/renderer/smartscreen_renderer`: dashboard composition and RGB565 encoding
- `packages/core/smartscreen_core`: config, updates, diagnostics, performance, stream controller
- `installers/bootstrap`: cross-platform installer bootstrap
- `tests/transcripts`: replay baseline transcripts

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
smartscreen doctor --export
smartscreen list-devices
smartscreen send-test-pattern --pattern quadrants
smartscreen benchmark --seconds 30
smartscreen updates check --channel stable
smartscreen replay --transcript tests/transcripts/rev_a_handshake_frame.jsonl
```

## Device Protocol

- Auto-detect serial device `VID=0x1A86`, `PID=0x5722`
- `115200`, `8N1`, `rtscts=true`
- HELLO (`0x45` x 6), orientation (`0x79`), display window (`0xC5`), raw RGB565 LE stream

## Installer UX

End users should install from release artifacts only (double-click, no terminal):

- Windows: `SmartScreenInstaller-windows-x64.exe`
- macOS: `SmartScreenInstaller-macos-<arch>.dmg`
- Linux: `SmartScreenInstaller-linux-<arch>.AppImage`

Direct app binaries are also published:

- `SmartScreen-windows-<arch>.exe`
- `SmartScreen-macos-<arch>.dmg`
- `SmartScreen-linux-<arch>.AppImage`

The bootstrap logic verifies `checksums.txt` before launching installers.

## CI / Release Notes

Release workflow is free-first by default:

- If signing secrets are absent, unsigned artifacts are still built and published.
- If signing secrets are present, platform signing/notarization is performed and verified.
- You can switch back to strict mode by setting `SMARTSCREEN_REQUIRE_SIGNING=1` in your build environment.

### Optional secrets for signed release job

- Windows: `WINDOWS_SIGNING_CERT_BASE64`, `WINDOWS_SIGNING_CERT_PASSWORD`
- macOS: `APPLE_SIGNING_CERT_BASE64`, `APPLE_SIGNING_CERT_PASSWORD`, `APPLE_SIGN_IDENTITY`, `APPLE_ID`, `APPLE_APP_PASSWORD`, `APPLE_TEAM_ID`, `APPLE_KEYCHAIN_PASSWORD`
- Linux: `LINUX_SIGNING_KEY_BASE64` (optional: `LINUX_SIGNING_FINGERPRINT`, `LINUX_SIGNING_KEY_PASSPHRASE`)

Linux GPG setup guide: `installers/linux/SETUP_GPG.md`
Linux secret helper script: `installers/linux/configure_gpg_signing.sh`
Optional hardware runner guide: `docs/SELF_HOSTED_RUNNER.md`

### Windows distribution (Option A)

Windows artifacts are currently published unsigned by default. End users will likely see SmartScreen/Unknown Publisher prompts until trusted Windows code-signing is added.

## Tests

```bash
python -m pytest -q
```

## Notes

- v1 targets one device class only (`1A86:5722`).
- Legacy `.pcdate` import is intentionally out-of-scope.
