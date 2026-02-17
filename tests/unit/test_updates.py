import json
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "core"))

from smartscreen_core.updates import UpdateService


class _FakeResponse:
    def __init__(self, payload: dict, etag: str = '"abc"'):
        self._payload = payload
        self.headers = {"ETag": etag}

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class UpdateServiceTests(unittest.TestCase):
    def test_stable_channel_update_available(self):
        payload = {
            "tag_name": "v0.2.0",
            "name": "v0.2.0",
            "body": "notes",
            "html_url": "https://example/release",
        }
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
            svc = UpdateService(repo="x/y")
            out = svc.check(current_version="0.1.0", channel="stable")
            self.assertTrue(out.update_available)
            self.assertEqual(out.latest_version, "0.2.0")

    def test_beta_channel_selects_prerelease(self):
        payload = [
            {"tag_name": "v0.2.0", "prerelease": False},
            {
                "tag_name": "v0.3.0-beta.1",
                "name": "beta",
                "prerelease": True,
                "body": "beta notes",
                "html_url": "https://example/beta",
            },
        ]
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
            svc = UpdateService(repo="x/y")
            out = svc.check(current_version="0.1.0", channel="beta")
            self.assertTrue(out.update_available)
            self.assertEqual(out.release_name, "beta")


if __name__ == "__main__":
    unittest.main()
