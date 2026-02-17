"""Shared installer bootstrap service used by CLI and GUI frontends."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .resolver import Asset, PlatformTarget, resolve_target, select_installer_asset


ProgressCallback = Callable[[str], None]


def fetch_release_assets(repo: str, version: str) -> list[Asset]:
    if version == "latest":
        url = f"https://api.github.com/repos/{repo}/releases/latest"
    else:
        url = f"https://api.github.com/repos/{repo}/releases/tags/{version}"

    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return [Asset(name=item["name"], url=item["browser_download_url"]) for item in payload.get("assets", [])]


def find_checksums_asset(assets: list[Asset]) -> Asset | None:
    for asset in assets:
        if asset.name.lower() == "checksums.txt":
            return asset
    return None


def download_file(url: str, dest: Path) -> Path:
    with urllib.request.urlopen(url, timeout=180) as response:
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
        return subprocess.call(["open", str(installer_path)])

    installer_path.chmod(installer_path.stat().st_mode | 0o111)
    return subprocess.call([str(installer_path)])


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

    installer = select_installer_asset(assets, target)
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
