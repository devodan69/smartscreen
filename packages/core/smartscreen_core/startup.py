"""Cross-platform launch-at-login configuration."""

from __future__ import annotations

import os
import platform
from pathlib import Path


def _windows_run_key_path() -> str:
    return r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"


def _set_windows_startup(enabled: bool, app_name: str, command: str) -> None:
    import winreg  # type: ignore

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _windows_run_key_path(), 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass


def _set_macos_startup(enabled: bool, app_name: str, command: str) -> None:
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    plist = launch_agents / f"com.smartscreen.{app_name}.plist"

    if not enabled:
        if plist.exists():
            plist.unlink()
        return

    plist.write_text(
        f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple Computer//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
  <key>Label</key>
  <string>com.smartscreen.{app_name}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{command}</string>
    <string>run</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
""",
        encoding="utf-8",
    )


def _set_linux_startup(enabled: bool, app_name: str, command: str) -> None:
    autostart_dir = Path.home() / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = autostart_dir / f"{app_name}.desktop"

    if not enabled:
        if desktop_file.exists():
            desktop_file.unlink()
        return

    desktop_file.write_text(
        f"""[Desktop Entry]
Type=Application
Name={app_name}
Exec={command} run
X-GNOME-Autostart-enabled=true
""",
        encoding="utf-8",
    )


def set_launch_at_login(enabled: bool, app_name: str = "SmartScreen", command: str | None = None) -> None:
    cmd = command or os.environ.get("SMARTSCREEN_CMD", "smartscreen")
    system = platform.system()

    if system == "Windows":
        _set_windows_startup(enabled, app_name, cmd)
    elif system == "Darwin":
        _set_macos_startup(enabled, app_name, cmd)
    else:
        _set_linux_startup(enabled, app_name, cmd)
