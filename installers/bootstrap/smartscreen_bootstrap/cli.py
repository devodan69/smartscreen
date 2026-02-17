"""CLI bootstrap installer that downloads and launches native package."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .service import download_installer, run_installer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smartscreen-bootstrap", description="SmartScreen installer bootstrap")
    parser.add_argument("--repo", default="devodan69/smartscreen", help="GitHub owner/repo")
    parser.add_argument("--version", default="latest", help="Release tag or 'latest'")
    parser.add_argument("--no-install", action="store_true", help="Resolve and download only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="smartscreen-install-") as tmp:
        result = download_installer(
            repo=args.repo,
            version=args.version,
            destination_dir=Path(tmp),
            progress=lambda _msg: None,
        )

        print(json.dumps({
            "target_os": result.target.os_name,
            "target_arch": result.target.arch,
            "asset": result.installer_asset.name,
            "path": str(result.installer_path),
            "install": not args.no_install,
        }, indent=2))

        if args.no_install:
            return 0

        return int(run_installer(result.installer_path, silent=True))


if __name__ == "__main__":
    raise SystemExit(main())
