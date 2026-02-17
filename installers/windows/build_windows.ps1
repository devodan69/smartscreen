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
$appOut = "dist/release/SmartScreen-windows-$arch.exe"
$installerOut = "dist/release/SmartScreenInstaller-windows-$arch.exe"
Copy-Item dist/SmartScreen.exe $appOut -Force
Copy-Item dist/SmartScreenInstaller.exe $installerOut -Force

$requireSigning = ($env:SMARTSCREEN_REQUIRE_SIGNING -eq "1")
$certB64 = $env:WINDOWS_SIGNING_CERT_BASE64
$certPwd = $env:WINDOWS_SIGNING_CERT_PASSWORD
$timestampUrl = if ($env:WINDOWS_TIMESTAMP_URL) { $env:WINDOWS_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }

function Sign-File($path, $certFile, $password, $tsUrl) {
  & signtool sign /fd SHA256 /f $certFile /p $password /tr $tsUrl /td SHA256 $path
  if ($LASTEXITCODE -ne 0) {
    throw "signtool sign failed for $path"
  }

  $sig = Get-AuthenticodeSignature -FilePath $path
  if ($sig.Status -ne "Valid") {
    throw "signature verification failed for $path status=$($sig.Status)"
  }
}

if ($certB64) {
  $certPath = Join-Path $env:RUNNER_TEMP "smartscreen-signing.pfx"
  [System.IO.File]::WriteAllBytes($certPath, [System.Convert]::FromBase64String($certB64))

  if (-not $certPwd) {
    throw "WINDOWS_SIGNING_CERT_PASSWORD is required when cert is provided"
  }

  Sign-File $appOut $certPath $certPwd $timestampUrl
  Sign-File $installerOut $certPath $certPwd $timestampUrl

  Remove-Item -Force $certPath
} elseif ($requireSigning) {
  throw "SMARTSCREEN_REQUIRE_SIGNING=1 but WINDOWS_SIGNING_CERT_BASE64 is missing"
}
