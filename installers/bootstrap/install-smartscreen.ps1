param(
  [string]$Repo = "dgeprojects/smartscreen",
  [string]$Version = "latest",
  [switch]$NoInstall
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($env:PYTHONPATH) {
  $env:PYTHONPATH = \"$scriptDir;$env:PYTHONPATH\"
} else {
  $env:PYTHONPATH = $scriptDir
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  Write-Error "Python is required for installer bootstrap"
  exit 1
}

$args = @("-m", "smartscreen_bootstrap.cli", "--repo", $Repo, "--version", $Version)
if ($NoInstall) { $args += "--no-install" }

& $python.Source @args
exit $LASTEXITCODE
