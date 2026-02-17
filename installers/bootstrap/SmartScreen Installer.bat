@echo off
set SCRIPT_DIR=%~dp0
if defined PYTHONPATH (
  set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%
) else (
  set PYTHONPATH=%SCRIPT_DIR%
)

where pythonw >nul 2>&1
if %errorlevel%==0 (
  pythonw -m smartscreen_bootstrap.gui
  exit /b %errorlevel%
)

where python >nul 2>&1
if %errorlevel%==0 (
  python -m smartscreen_bootstrap.gui
  exit /b %errorlevel%
)

echo Python is required for SmartScreen installer UI.
exit /b 1
