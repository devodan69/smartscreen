"""Structured local logging and crash hook setup."""

from __future__ import annotations

import faulthandler
import json
import logging
import logging.handlers
import os
import platform
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_LOGGER_NAME = "smartscreen"


def _config_root() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "SmartScreen"
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "SmartScreen"
    return Path.home() / ".config" / "smartscreen"


def log_dir() -> Path:
    path = _config_root() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if hasattr(record, "event"):
            payload["event"] = getattr(record, "event")
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(keep_files: int = 7, console: bool = True) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    path = log_dir() / "smartscreen.log"
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(path),
        when="midnight",
        backupCount=max(2, keep_files),
        encoding="utf-8",
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(stream_handler)

    logger.info("logging configured", extra={"event": "logging_configured"})
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def _install_fault_handler(logger: logging.Logger) -> None:
    fault_path = log_dir() / "fault.log"
    fh = fault_path.open("a", encoding="utf-8")
    faulthandler.enable(file=fh, all_threads=True)
    logger.info("fault handler enabled", extra={"event": "fault_handler_enabled"})


def install_crash_hooks() -> None:
    logger = get_logger()

    def _log_uncaught(exc_type, exc_value, exc_tb) -> None:
        crash_id = str(uuid.uuid4())
        logger.critical(
            f"uncaught exception crash_id={crash_id}",
            exc_info=(exc_type, exc_value, exc_tb),
            extra={"event": "uncaught_exception", "crash_id": crash_id},
        )

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        crash_id = str(uuid.uuid4())
        logger.critical(
            f"thread exception crash_id={crash_id}",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            extra={"event": "thread_exception", "crash_id": crash_id},
        )

    sys.excepthook = _log_uncaught
    threading.excepthook = _thread_hook
    _install_fault_handler(logger)
