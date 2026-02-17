#!/usr/bin/env bash
set -euo pipefail

python -m PyInstaller --noconfirm --onefile --windowed --name SmartScreen apps/desktop/smartscreen_app/__main__.py
python -m PyInstaller --noconfirm --onefile --windowed --name SmartScreenInstaller installers/bootstrap/smartscreen_bootstrap/gui.py

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
HERE="\$(dirname \"\$(readlink -f \"\$0\")\")"
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
