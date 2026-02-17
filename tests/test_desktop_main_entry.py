from __future__ import annotations

import runpy
from pathlib import Path

import smartscreen_app.__main__ as desktop_main


def test_main_defaults_to_run(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(desktop_main, "_cli_main", lambda argv=None: calls.append(list(argv or [])) or 0)

    rc = desktop_main.main([])
    assert rc == 0
    assert calls == [["run"]]


def test_main_passes_through_args(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(desktop_main, "_cli_main", lambda argv=None: calls.append(list(argv or [])) or 0)

    rc = desktop_main.main(["doctor", "--export"])
    assert rc == 0
    assert calls == [["doctor", "--export"]]


def test_main_module_runpath_without_package_context() -> None:
    main_path = (
        Path(__file__).resolve().parents[1]
        / "apps"
        / "desktop"
        / "smartscreen_app"
        / "__main__.py"
    )
    result = runpy.run_path(str(main_path))
    assert "main" in result
