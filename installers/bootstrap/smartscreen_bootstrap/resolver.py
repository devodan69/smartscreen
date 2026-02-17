"""Release asset resolution for OS/architecture specific installers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformTarget:
    os_name: str
    arch: str


@dataclass(frozen=True)
class Asset:
    name: str
    url: str


def _normalize_os(system: str) -> str:
    s = system.lower()
    if s.startswith("win"):
        return "windows"
    if s.startswith("darwin") or s.startswith("mac"):
        return "macos"
    return "linux"


def _normalize_arch(machine: str) -> str:
    m = machine.lower()
    if m in ("x86_64", "amd64"):
        return "x64"
    if m in ("aarch64", "arm64"):
        return "arm64"
    return m


def resolve_target(system: str, machine: str) -> PlatformTarget:
    return PlatformTarget(os_name=_normalize_os(system), arch=_normalize_arch(machine))


def expected_suffix(target: PlatformTarget) -> str:
    if target.os_name == "windows":
        return ".exe"
    if target.os_name == "macos":
        return ".dmg"
    return ".AppImage"


def select_asset(assets: list[Asset], target: PlatformTarget) -> Asset:
    suffix = expected_suffix(target)
    needle_os = target.os_name
    needle_arch = target.arch

    for asset in assets:
        lower = asset.name.lower()
        if needle_os in lower and needle_arch in lower and lower.endswith(suffix.lower()):
            return asset

    for asset in assets:
        lower = asset.name.lower()
        if needle_os in lower and lower.endswith(suffix.lower()):
            return asset

    raise RuntimeError(f"No installer asset found for {target.os_name}/{target.arch}")


def select_installer_asset(assets: list[Asset], target: PlatformTarget) -> Asset:
    """Prefer installer-branded assets when multiple candidates match."""
    suffix = expected_suffix(target)
    os_name = target.os_name.lower()
    arch = target.arch.lower()

    def _is_candidate(a: Asset) -> bool:
        lower = a.name.lower()
        if not lower.endswith(suffix.lower()):
            return False
        if os_name not in lower:
            return False
        if arch in ("x64", "arm64"):
            return arch in lower or "universal" in lower
        return True

    candidates = [a for a in assets if _is_candidate(a)]
    if not candidates:
        return select_asset(assets, target)

    def _rank(name: str) -> tuple[int, int]:
        lower = name.lower()
        installer_score = 0
        if "installer" in lower:
            installer_score += 10
        if lower.startswith("smartscreeninstaller"):
            installer_score += 8
        if lower.startswith("smartscreen-installer"):
            installer_score += 8
        if "bootstrap" in lower:
            installer_score += 3

        arch_score = 1 if arch in lower else 0
        return (installer_score, arch_score)

    candidates.sort(key=lambda a: _rank(a.name), reverse=True)
    return candidates[0]
