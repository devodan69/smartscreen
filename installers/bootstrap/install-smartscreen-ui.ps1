param()

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($env:PYTHONPATH) {
  $env:PYTHONPATH = \"$scriptDir;$env:PYTHONPATH\"
} else {
  $env:PYTHONPATH = $scriptDir
}

$pythonw = Get-Command pythonw -ErrorAction SilentlyContinue
if ($pythonw) {
  & $pythonw.Source "-m" "smartscreen_bootstrap.gui"
  exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  Write-Error "Python is required for SmartScreen installer UI"
  exit 1
}

& $python.Source "-m" "smartscreen_bootstrap.gui"
exit $LASTEXITCODE
