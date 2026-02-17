param()

$ErrorActionPreference = "Stop"

python -m PyInstaller --noconfirm --onefile --windowed --name SmartScreen apps/desktop/smartscreen_app/__main__.py
python -m PyInstaller --noconfirm --onefile --windowed --name SmartScreenInstaller installers/bootstrap/smartscreen_bootstrap/gui.py

$archRaw = $env:PROCESSOR_ARCHITECTURE
if ($archRaw -eq "AMD64") {
  $arch = "x64"
} elseif ($archRaw -eq "ARM64") {
  $arch = "arm64"
} else {
  $arch = $archRaw.ToLower()
}

New-Item -ItemType Directory -Force -Path dist/release | Out-Null
Copy-Item dist/SmartScreen.exe "dist/release/SmartScreen-windows-$arch.exe" -Force
Copy-Item dist/SmartScreenInstaller.exe "dist/release/SmartScreenInstaller-windows-$arch.exe" -Force
