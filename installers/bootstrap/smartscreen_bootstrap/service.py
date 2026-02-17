"""Shared installer bootstrap service used by CLI and GUI frontends."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import plistlib
import shutil
import ssl
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .resolver import Asset, PlatformTarget, resolve_target, select_runtime_asset

try:
    import certifi
except Exception:  # pragma: no cover - fallback when optional dependency unavailable
    certifi = None


ProgressCallback = Callable[[str], None]


def _build_ssl_context() -> ssl.SSLContext:
    """Create TLS context for installer downloads with explicit CA handling."""
    if os.environ.get("SMARTSCREEN_ALLOW_INSECURE_TLS", "").strip() == "1":
        return ssl._create_unverified_context()

    ca_bundle = os.environ.get("SMARTSCREEN_CA_BUNDLE", "").strip()
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)

    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())

    return ssl.create_default_context()


def _urlopen(url: str, timeout: int, accept: str = "*/*"):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SmartScreenInstaller/0.1 (+https://github.com/devodan69/smartscreen)",
            "Accept": accept,
        },
    )
    return urllib.request.urlopen(request, timeout=timeout, context=_build_ssl_context())


def fetch_release_assets(repo: str, version: str) -> list[Asset]:
    if version == "latest":
        url = f"https://api.github.com/repos/{repo}/releases/latest"
    else:
        url = f"https://api.github.com/repos/{repo}/releases/tags/{version}"

    with _urlopen(url, timeout=30, accept="application/vnd.github+json") as response:
        payload = json.loads(response.read().decode("utf-8"))

    return [Asset(name=item["name"], url=item["browser_download_url"]) for item in payload.get("assets", [])]


def find_checksums_asset(assets: list[Asset]) -> Asset | None:
    for asset in assets:
        if asset.name.lower() == "checksums.txt":
            return asset
    return None


def download_file(url: str, dest: Path) -> Path:
    with _urlopen(url, timeout=180) as response:
        dest.write_bytes(response.read())
    return dest


def parse_checksums(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            out[parts[1]] = parts[0]
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(installer_path: Path, checksums_path: Path) -> bool:
    checksums = parse_checksums(checksums_path)
    expected = checksums.get(installer_path.name)
    if not expected:
        return True
    digest = sha256_file(installer_path)
    return digest.lower() == expected.lower()


def run_installer(installer_path: Path, silent: bool = False) -> int:
    system = platform.system().lower()
    if system.startswith("win"):
        if silent:
            return subprocess.call([str(installer_path), "/VERYSILENT"])
        return subprocess.call([str(installer_path)])
    if system.startswith("darwin"):
        if installer_path.suffix.lower() == ".dmg":
            return _install_from_macos_dmg(installer_path)
        return subprocess.call(["open", str(installer_path)])

    installer_path.chmod(installer_path.stat().st_mode | 0o111)
    return subprocess.call([str(installer_path)])


def _install_from_macos_dmg(dmg_path: Path) -> int:
    """Mount a macOS DMG, copy app bundle to Applications, and launch it."""
    attach_cmd = ["hdiutil", "attach", "-nobrowse", "-readonly", "-plist", str(dmg_path)]
    attach_output = subprocess.check_output(attach_cmd)
    plist = plistlib.loads(attach_output)

    mount_points: list[Path] = []
    for ent in plist.get("system-entities", []):
        mount = ent.get("mount-point")
        if mount:
            mount_points.append(Path(mount))

    if not mount_points:
        raise RuntimeError("Could not mount DMG: no mount point found")

    mount_point = mount_points[0]
    last_error: Exception | None = None
    app_candidates = sorted(mount_point.glob("*.app"))
    if not app_candidates:
        # Fallback: open mounted DMG in Finder if app cannot be located.
        subprocess.call(["open", str(mount_point)])
        return 0

    app_src = app_candidates[0]
    target_dirs = [Path("/Applications"), Path.home() / "Applications"]

    try:
        for target_dir in target_dirs:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                target_app = target_dir / app_src.name
                if target_app.exists():
                    shutil.rmtree(target_app)
                shutil.copytree(app_src, target_app, dirs_exist_ok=True)
                subprocess.call(["xattr", "-dr", "com.apple.quarantine", str(target_app)])
                subprocess.call(["open", str(target_app)])
                return 0
            except PermissionError as exc:
                last_error = exc
            except OSError as exc:
                last_error = exc
    finally:
        subprocess.call(["hdiutil", "detach", str(mount_point), "-quiet"])

    if last_error is not None:
        raise RuntimeError(f"Install failed: {last_error}") from last_error
    raise RuntimeError("Install failed: no writable Applications directory")


@dataclass(frozen=True)
class DownloadResult:
    target: PlatformTarget
    installer_asset: Asset
    installer_path: Path
    checksums_path: Path | None


def download_installer(
    repo: str,
    version: str,
    destination_dir: Path,
    progress: ProgressCallback | None = None,
) -> DownloadResult:
    progress = progress or (lambda _msg: None)
    progress("Resolving release assets")
    target = resolve_target(platform.system(), platform.machine())

    assets = fetch_release_assets(repo, version)
    progress(f"Detected target {target.os_name}/{target.arch}")

    installer = select_runtime_asset(assets, target)
    checksums_asset = find_checksums_asset(assets)

    destination_dir.mkdir(parents=True, exist_ok=True)
    installer_path = destination_dir / installer.name

    progress(f"Downloading {installer.name}")
    download_file(installer.url, installer_path)

    checksums_path: Path | None = None
    if checksums_asset is not None:
        progress("Downloading checksums")
        checksums_path = destination_dir / checksums_asset.name
        download_file(checksums_asset.url, checksums_path)

        progress("Verifying checksum")
        if not verify_checksum(installer_path, checksums_path):
            raise RuntimeError("Checksum verification failed")

    progress("Download complete")
    return DownloadResult(
        target=target,
        installer_asset=installer,
        installer_path=installer_path,
        checksums_path=checksums_path,
    )
