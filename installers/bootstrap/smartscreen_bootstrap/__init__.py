"""Bootstrap installer resolver and runner for SmartScreen."""

from .resolver import (
    Asset,
    PlatformTarget,
    resolve_target,
    select_asset,
    select_installer_asset,
    select_runtime_asset,
)
from .service import DownloadResult, download_installer, fetch_release_assets, run_installer

__all__ = [
    "Asset",
    "DownloadResult",
    "PlatformTarget",
    "download_installer",
    "fetch_release_assets",
    "resolve_target",
    "run_installer",
    "select_asset",
    "select_installer_asset",
    "select_runtime_asset",
]
