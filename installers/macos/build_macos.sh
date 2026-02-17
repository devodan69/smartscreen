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
app_dmg="dist/release/SmartScreen-macos-${arch}.dmg"
installer_dmg="dist/release/SmartScreenInstaller-macos-${arch}.dmg"

hdiutil create -volname "SmartScreen" -srcfolder dist/SmartScreen.app -ov -format UDZO "$app_dmg"
hdiutil create -volname "SmartScreen Installer" -srcfolder dist/SmartScreenInstaller.app -ov -format UDZO "$installer_dmg"

require_signing="${SMARTSCREEN_REQUIRE_SIGNING:-0}"
identity="${SMARTSCREEN_MAC_SIGN_IDENTITY:-}"
apple_id="${APPLE_ID:-}"
apple_password="${APPLE_APP_PASSWORD:-}"
apple_team_id="${APPLE_TEAM_ID:-}"

if [[ -n "$identity" ]]; then
  codesign --deep --force --options runtime --timestamp --sign "$identity" dist/SmartScreen.app
  codesign --deep --force --options runtime --timestamp --sign "$identity" dist/SmartScreenInstaller.app
  codesign --force --timestamp --sign "$identity" "$app_dmg"
  codesign --force --timestamp --sign "$identity" "$installer_dmg"

  codesign --verify --deep --strict dist/SmartScreen.app
  codesign --verify --deep --strict dist/SmartScreenInstaller.app

  if [[ -n "$apple_id" && -n "$apple_password" && -n "$apple_team_id" ]]; then
    xcrun notarytool submit "$app_dmg" --apple-id "$apple_id" --password "$apple_password" --team-id "$apple_team_id" --wait
    xcrun notarytool submit "$installer_dmg" --apple-id "$apple_id" --password "$apple_password" --team-id "$apple_team_id" --wait
    xcrun stapler staple "$app_dmg"
    xcrun stapler staple "$installer_dmg"
  elif [[ "$require_signing" == "1" ]]; then
    echo "SMARTSCREEN_REQUIRE_SIGNING=1 but notarization credentials missing" >&2
    exit 1
  fi
elif [[ "$require_signing" == "1" ]]; then
  echo "SMARTSCREEN_REQUIRE_SIGNING=1 but SMARTSCREEN_MAC_SIGN_IDENTITY missing" >&2
  exit 1
fi
