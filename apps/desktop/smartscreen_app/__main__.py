from __future__ import annotations

import sys

try:
    # Normal package import path.
    from .cli import main as _cli_main
except ImportError:
    # Script/frozen entrypoint path.
    from smartscreen_app.cli import main as _cli_main


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        # Double-click app bundle should open GUI by default.
        return int(_cli_main(["run"]))
    return int(_cli_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
