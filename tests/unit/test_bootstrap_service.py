import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "installers" / "bootstrap"))

from smartscreen_bootstrap.service import parse_checksums, sha256_file, verify_checksum


class BootstrapServiceTests(unittest.TestCase):
    def test_parse_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "checksums.txt"
            p.write_text("abc123 file-a.exe\nfff999 file-b.dmg\n", encoding="utf-8")
            parsed = parse_checksums(p)
            self.assertEqual(parsed["file-a.exe"], "abc123")
            self.assertEqual(parsed["file-b.dmg"], "fff999")

    def test_sha256_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installer = root / "thing.exe"
            installer.write_bytes(b"hello world")

            digest = hashlib.sha256(b"hello world").hexdigest()
            self.assertEqual(sha256_file(installer), digest)

            checksums = root / "checksums.txt"
            checksums.write_text(f"{digest} {installer.name}\n", encoding="utf-8")
            self.assertTrue(verify_checksum(installer, checksums))

            checksums.write_text(f"deadbeef {installer.name}\n", encoding="utf-8")
            self.assertFalse(verify_checksum(installer, checksums))


if __name__ == "__main__":
    unittest.main()
