#!/usr/bin/env bash
set -euo pipefail

python -m PyInstaller --noconfirm --windowed --name SmartScreen apps/desktop/smartscreen_app/__main__.py
python -m PyInstaller --noconfirm --windowed --name SmartScreenInstaller installers/bootstrap/smartscreen_bootstrap/gui.py

arch_raw="$(uname -m)"
case "$arch_raw" in
  x86_64) arch="x64" ;;
  arm64|aarch64) arch="arm64" ;;
  *) arch="$arch_raw" ;;
esac

mkdir -p dist/release
hdiutil create -volname "SmartScreen" -srcfolder dist/SmartScreen.app -ov -format UDZO "dist/release/SmartScreen-macos-${arch}.dmg"
hdiutil create -volname "SmartScreen Installer" -srcfolder dist/SmartScreenInstaller.app -ov -format UDZO "dist/release/SmartScreenInstaller-macos-${arch}.dmg"
