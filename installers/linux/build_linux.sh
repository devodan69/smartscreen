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

python -m PyInstaller --noconfirm --onefile --windowed --name SmartScreen "${COMMON_APP_ARGS[@]}" apps/desktop/smartscreen_app/__main__.py
python -m PyInstaller --noconfirm --onefile --windowed --name SmartScreenInstaller "${COMMON_INSTALLER_ARGS[@]}" installers/bootstrap/smartscreen_bootstrap/gui.py

arch_raw="$(uname -m)"
case "$arch_raw" in
  x86_64) arch="x64" ;;
  aarch64|arm64) arch="arm64" ;;
  *) arch="$arch_raw" ;;
esac

APPIMAGE_TOOL="${APPIMAGE_TOOL:-installers/linux/appimagetool}"
if [[ ! -x "$APPIMAGE_TOOL" ]]; then
  echo "appimagetool not found at $APPIMAGE_TOOL"
  exit 1
fi

mkdir -p dist/release dist/linux

make_icon() {
  local output="$1"
  python - <<'PY' "$output"
from PIL import Image, ImageDraw
import sys
out = sys.argv[1]
img = Image.new("RGB", (256, 256), (16, 26, 46))
d = ImageDraw.Draw(img)
d.rounded_rectangle((22, 22, 234, 234), radius=40, outline=(46, 206, 246), width=10)
d.text((54, 100), "SS", fill=(220, 240, 255))
img.save(out)
PY
}

make_appimage() {
  local name="$1"
  local bin_name="$2"
  local appdir="dist/linux/${name}.AppDir"
  local desktop_file="${name}.desktop"
  local icon_file="${name}.png"

  rm -rf "$appdir"
  mkdir -p "$appdir/usr/bin" "$appdir/usr/share/applications" "$appdir/usr/share/icons/hicolor/256x256/apps"

  cp "dist/${bin_name}" "$appdir/usr/bin/${bin_name}"
  chmod +x "$appdir/usr/bin/${bin_name}"

  cat > "$appdir/AppRun" <<EOS
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\$0")")"
exec "\$HERE/usr/bin/${bin_name}" "\$@"
EOS
  chmod +x "$appdir/AppRun"

  cat > "$appdir/${desktop_file}" <<EOS
[Desktop Entry]
Type=Application
Name=${name}
Exec=${bin_name}
Icon=${name}
Categories=Utility;
Terminal=false
EOS

  cp "$appdir/${desktop_file}" "$appdir/usr/share/applications/${desktop_file}"

  make_icon "$appdir/${icon_file}"
  cp "$appdir/${icon_file}" "$appdir/usr/share/icons/hicolor/256x256/apps/${icon_file}"

  APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$arch_raw" "$APPIMAGE_TOOL" "$appdir" "dist/release/${name}-linux-${arch}.AppImage"
}

make_appimage "SmartScreen" "SmartScreen"
make_appimage "SmartScreenInstaller" "SmartScreenInstaller"

require_signing="${SMARTSCREEN_REQUIRE_SIGNING:-0}"
gpg_key_b64="${LINUX_SIGNING_KEY_BASE64:-}"
gpg_fingerprint="${LINUX_SIGNING_FINGERPRINT:-}"
gpg_passphrase="${LINUX_SIGNING_KEY_PASSPHRASE:-}"

if [[ -n "$gpg_key_b64" ]]; then
  export GNUPGHOME
  GNUPGHOME="$(mktemp -d)"
  trap 'rm -rf "$GNUPGHOME"' EXIT

  echo "$gpg_key_b64" | base64 --decode > "$GNUPGHOME/signing.key"
  gpg --batch --import "$GNUPGHOME/signing.key"

  if [[ -z "$gpg_fingerprint" ]]; then
    gpg_fingerprint="$(gpg --list-secret-keys --with-colons | awk -F: '/^fpr:/ {print $10; exit}')"
  fi

  for f in dist/release/*.AppImage; do
    if [[ -n "$gpg_passphrase" ]]; then
      gpg --batch --yes --pinentry-mode loopback --passphrase "$gpg_passphrase" --local-user "$gpg_fingerprint" --output "$f.sig" --armor --detach-sign "$f"
    else
      gpg --batch --yes --pinentry-mode loopback --local-user "$gpg_fingerprint" --output "$f.sig" --armor --detach-sign "$f"
    fi
  done
elif [[ "$require_signing" == "1" ]]; then
  echo "SMARTSCREEN_REQUIRE_SIGNING=1 but LINUX_SIGNING_KEY_BASE64 missing" >&2
  exit 1
fi
