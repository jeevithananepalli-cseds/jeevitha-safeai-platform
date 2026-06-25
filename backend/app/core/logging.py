"""Application logging configuration.

A single ``configure_logging`` entry point sets up consistent, structured-ish
console logging for the whole process. Keeping this in one place means every
module uses the same format and level, and we never sprinkle ``print`` calls.

Design choices:

* Log to stdout — the right target for containers (the orchestrator collects it).
* Include timestamp, level, logger name, and message.
* Level is driven by configuration, not hard-coded.
* Secrets and PII must never be logged (enforced by review, not format).
"""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once.

    Idempotent: safe to call from both the app factory and tests without
    stacking duplicate handlers.

    Args:
        level: Logging level name (e.g. ``"INFO"``, ``"DEBUG"``).
    """
    global _configured

    numeric_level = logging.getLevelName(level.upper())
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    root = logging.getLogger()
    root.setLevel(numeric_level)

    if not _configured:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))
        root.handlers.clear()
        root.addHandler(stream_handler)
        _configured = True
    else:
        for existing_handler in root.handlers:
            existing_handler.setLevel(numeric_level)

    # Align uvicorn's loggers with ours so output is uniform.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).setLevel(numeric_level)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Thin wrapper for a single import surface."""
    return logging.getLogger(name)
