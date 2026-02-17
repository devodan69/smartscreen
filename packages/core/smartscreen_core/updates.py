"""Manual release channel update checks against GitHub Releases API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class UpdateCheckResult:
    checked_at_utc: str
    channel: str
    update_available: bool
    latest_version: str | None
    release_name: str | None
    notes: str | None
    download_url: str | None
    etag: str | None
    not_modified: bool = False


class UpdateService:
    def __init__(self, repo: str = "devodan69/smartscreen") -> None:
        self.repo = repo

    @staticmethod
    def _normalize_channel(channel: str) -> str:
        return "beta" if channel == "beta" else "stable"

    @staticmethod
    def _extract_version(tag_name: str | None) -> str | None:
        if not tag_name:
            return None
        return tag_name[1:] if tag_name.startswith("v") else tag_name

    @staticmethod
    def _is_newer(current_version: str, latest_version: str | None) -> bool:
        if not latest_version:
            return False
        if current_version == latest_version:
            return False

        def _parts(v: str) -> tuple[int, ...]:
            out = []
            for p in v.replace("-", ".").split("."):
                try:
                    out.append(int(p))
                except ValueError:
                    out.append(0)
            return tuple(out)

        return _parts(latest_version) > _parts(current_version)

    def check(
        self,
        current_version: str,
        channel: str = "stable",
        etag: str | None = None,
        timeout_s: int = 30,
    ) -> UpdateCheckResult:
        channel_norm = self._normalize_channel(channel)
        checked = datetime.now(timezone.utc).isoformat()

        if channel_norm == "stable":
            url = f"https://api.github.com/repos/{self.repo}/releases/latest"
            req = urllib.request.Request(url)
            if etag:
                req.add_header("If-None-Match", etag)

            try:
                with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    resp_etag = resp.headers.get("ETag")
            except urllib.error.HTTPError as exc:
                if exc.code == 304:
                    return UpdateCheckResult(
                        checked_at_utc=checked,
                        channel=channel_norm,
                        update_available=False,
                        latest_version=None,
                        release_name=None,
                        notes=None,
                        download_url=None,
                        etag=etag,
                        not_modified=True,
                    )
                raise

            latest = self._extract_version(payload.get("tag_name"))
            return UpdateCheckResult(
                checked_at_utc=checked,
                channel=channel_norm,
                update_available=self._is_newer(current_version, latest),
                latest_version=latest,
                release_name=payload.get("name"),
                notes=(payload.get("body") or "")[:4000],
                download_url=payload.get("html_url"),
                etag=resp_etag,
                not_modified=False,
            )

        # Beta channel: inspect list for prerelease entries.
        url = f"https://api.github.com/repos/{self.repo}/releases"
        req = urllib.request.Request(url)
        if etag:
            req.add_header("If-None-Match", etag)

        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                resp_etag = resp.headers.get("ETag")
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                return UpdateCheckResult(
                    checked_at_utc=checked,
                    channel=channel_norm,
                    update_available=False,
                    latest_version=None,
                    release_name=None,
                    notes=None,
                    download_url=None,
                    etag=etag,
                    not_modified=True,
                )
            raise

        prerelease = None
        for rel in payload:
            if rel.get("prerelease"):
                prerelease = rel
                break

        latest = self._extract_version(prerelease.get("tag_name") if prerelease else None)
        return UpdateCheckResult(
            checked_at_utc=checked,
            channel=channel_norm,
            update_available=self._is_newer(current_version, latest),
            latest_version=latest,
            release_name=(prerelease.get("name") if prerelease else None),
            notes=((prerelease.get("body") or "")[:4000] if prerelease else None),
            download_url=(prerelease.get("html_url") if prerelease else None),
            etag=resp_etag,
            not_modified=False,
        )
