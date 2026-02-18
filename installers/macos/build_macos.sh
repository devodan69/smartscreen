#!/usr/bin/env bash
set -euo pipefail

COMMON_APP_ARGS=(
  --paths apps/desktop
  --paths installers/bootstrap
  --paths packages/core
  --paths packages/display_protocol
  --paths packages/renderer
  --paths packages/telemetry
  --collect-submodules smartscreen_app
  --collect-submodules smartscreen_core
  --collect-submodules smartscreen_display
  --collect-submodules smartscreen_renderer
  --collect-submodules smartscreen_telemetry
  --collect-data smartscreen_app
)

COMMON_INSTALLER_ARGS=(
  --paths installers/bootstrap
  --collect-submodules smartscreen_bootstrap
)

python -m PyInstaller --noconfirm --windowed --name SmartScreen "${COMMON_APP_ARGS[@]}" apps/desktop/smartscreen_app/__main__.py
python -m PyInstaller --noconfirm --windowed --name SmartScreenInstaller "${COMMON_INSTALLER_ARGS[@]}" installers/bootstrap/smartscreen_bootstrap/gui.py

arch_raw="$(uname -m)"
case "$arch_raw" in
  x86_64) arch="x64" ;;
  arm64|aarch64) arch="arm64" ;;
  *) arch="$arch_raw" ;;
esac

mkdir -p dist/release
app_dmg="dist/release/SmartScreen-macos-${arch}.dmg"
installer_dmg="dist/release/SmartScreenInstaller-macos-${arch}.dmg"

require_signing="${SMARTSCREEN_REQUIRE_SIGNING:-0}"
identity="${SMARTSCREEN_MAC_SIGN_IDENTITY:-}"
apple_id="${APPLE_ID:-}"
apple_password="${APPLE_APP_PASSWORD:-}"
apple_team_id="${APPLE_TEAM_ID:-}"

if [[ -n "$identity" ]]; then
  # Sign app bundles before packaging so DMGs contain signed binaries.
  codesign --deep --force --options runtime --timestamp --sign "$identity" dist/SmartScreen.app
  codesign --deep --force --options runtime --timestamp --sign "$identity" dist/SmartScreenInstaller.app

  codesign --verify --deep --strict dist/SmartScreen.app
  codesign --verify --deep --strict dist/SmartScreenInstaller.app
elif [[ "$require_signing" == "1" ]]; then
  echo "SMARTSCREEN_REQUIRE_SIGNING=1 but SMARTSCREEN_MAC_SIGN_IDENTITY missing" >&2
  exit 1
fi

rm -f "$app_dmg" "$installer_dmg"
hdiutil create -volname "SmartScreen" -srcfolder dist/SmartScreen.app -ov -format UDZO "$app_dmg"
hdiutil create -volname "SmartScreen Installer" -srcfolder dist/SmartScreenInstaller.app -ov -format UDZO "$installer_dmg"

if [[ -n "$identity" ]]; then
  codesign --force --timestamp --sign "$identity" "$app_dmg"
  codesign --force --timestamp --sign "$identity" "$installer_dmg"

  if [[ -n "$apple_id" && -n "$apple_password" && -n "$apple_team_id" ]]; then
    notarize_file() {
      local target="$1"
      local submit_json status submission_id

      submit_json="$(xcrun notarytool submit "$target" --apple-id "$apple_id" --password "$apple_password" --team-id "$apple_team_id" --wait --output-format json)"
      status="$(python -c "import json,sys; print(json.load(sys.stdin).get('status', ''))" <<< "$submit_json")"
      if [[ "$status" != "Accepted" ]]; then
        submission_id="$(python -c "import json,sys; print(json.load(sys.stdin).get('id', ''))" <<< "$submit_json")"
        if [[ -n "$submission_id" ]]; then
          xcrun notarytool log "$submission_id" --apple-id "$apple_id" --password "$apple_password" --team-id "$apple_team_id" > "${target}.notary.json" || true
          echo "Saved notarization log to ${target}.notary.json" >&2
        fi
        echo "Notarization status for ${target}: ${status}" >&2
        return 1
      fi
      return 0
    }

    if notarize_file "$app_dmg" && notarize_file "$installer_dmg"; then
      xcrun stapler staple "$app_dmg"
      xcrun stapler staple "$installer_dmg"
      touch dist/release/.notarization_succeeded
    elif [[ "$require_signing" == "1" ]]; then
      echo "SMARTSCREEN_REQUIRE_SIGNING=1 but notarization failed" >&2
      exit 1
    else
      echo "Warning: notarization failed; continuing because SMARTSCREEN_REQUIRE_SIGNING=0" >&2
    fi
  elif [[ "$require_signing" == "1" ]]; then
    echo "SMARTSCREEN_REQUIRE_SIGNING=1 but notarization credentials missing" >&2
    exit 1
  fi
fi
