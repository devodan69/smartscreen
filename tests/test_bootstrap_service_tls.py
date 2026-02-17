from __future__ import annotations

import installers.bootstrap.smartscreen_bootstrap.service as service
from installers.bootstrap.smartscreen_bootstrap.resolver import Asset


def test_build_ssl_context_prefers_env_bundle(monkeypatch) -> None:
    calls: dict[str, str | None] = {}

    def fake_create_default_context(*, cafile=None):
        calls["cafile"] = cafile
        return object()

    monkeypatch.setattr(service.ssl, "create_default_context", fake_create_default_context)
    monkeypatch.setenv("SMARTSCREEN_CA_BUNDLE", "/tmp/custom-ca.pem")
    monkeypatch.delenv("SMARTSCREEN_ALLOW_INSECURE_TLS", raising=False)

    ctx = service._build_ssl_context()
    assert ctx is not None
    assert calls["cafile"] == "/tmp/custom-ca.pem"


def test_build_ssl_context_uses_unverified_flag(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setenv("SMARTSCREEN_ALLOW_INSECURE_TLS", "1")
    monkeypatch.delenv("SMARTSCREEN_CA_BUNDLE", raising=False)
    monkeypatch.setattr(service.ssl, "_create_unverified_context", lambda: sentinel)

    ctx = service._build_ssl_context()
    assert ctx is sentinel


def test_build_ssl_context_uses_certifi_bundle(monkeypatch) -> None:
    calls: dict[str, str | None] = {}

    def fake_create_default_context(*, cafile=None):
        calls["cafile"] = cafile
        return object()

    class FakeCertifi:
        @staticmethod
        def where() -> str:
            return "/tmp/certifi.pem"

    monkeypatch.setattr(service.ssl, "create_default_context", fake_create_default_context)
    monkeypatch.setattr(service, "certifi", FakeCertifi)
    monkeypatch.delenv("SMARTSCREEN_ALLOW_INSECURE_TLS", raising=False)
    monkeypatch.delenv("SMARTSCREEN_CA_BUNDLE", raising=False)

    ctx = service._build_ssl_context()
    assert ctx is not None
    assert calls["cafile"] == "/tmp/certifi.pem"


def test_download_installer_prefers_runtime_asset(monkeypatch, tmp_path) -> None:
    assets = [
        Asset(name="SmartScreenInstaller-macos-arm64.dmg", url="https://example/installer.dmg"),
        Asset(name="SmartScreen-macos-arm64.dmg", url="https://example/app.dmg"),
        Asset(name="checksums.txt", url="https://example/checksums.txt"),
    ]

    monkeypatch.setattr(service.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(service.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(service, "fetch_release_assets", lambda repo, version: assets)

    def fake_download_file(url: str, dest):
        if dest.name == "checksums.txt":
            dest.write_text("", encoding="utf-8")
        else:
            dest.write_bytes(b"payload")
        return dest

    monkeypatch.setattr(service, "download_file", fake_download_file)

    result = service.download_installer(
        repo="devodan69/smartscreen",
        version="latest",
        destination_dir=tmp_path,
        progress=lambda _msg: None,
    )
    assert "installer" not in result.installer_asset.name.lower()
    assert result.installer_path.name == "SmartScreen-macos-arm64.dmg"


def test_run_installer_uses_macos_dmg_path(monkeypatch, tmp_path) -> None:
    dmg_path = tmp_path / "SmartScreen-macos-arm64.dmg"
    dmg_path.write_bytes(b"fake")
    monkeypatch.setattr(service.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(service, "_install_from_macos_dmg", lambda _p: 0)

    code = service.run_installer(dmg_path, silent=False)
    assert code == 0
