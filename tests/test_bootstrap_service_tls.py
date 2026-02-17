from __future__ import annotations

import installers.bootstrap.smartscreen_bootstrap.service as service


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
