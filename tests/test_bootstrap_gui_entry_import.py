"""Regression test for bootstrap GUI script-style import path."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest


def test_gui_script_path_imports_without_package_context() -> None:
    pytest.importorskip("tkinter")

    gui_path = (
        Path(__file__).resolve().parents[1]
        / "installers"
        / "bootstrap"
        / "smartscreen_bootstrap"
        / "gui.py"
    )

    result = runpy.run_path(str(gui_path))
    assert "InstallerWindow" in result
    assert "main" in result
