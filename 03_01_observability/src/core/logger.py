# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Structured JSON logger — mirrors src/core/logger.ts.

Each call emits a single-line JSON object to stdout (or stderr for
error/warn).  Child loggers inherit parent bindings and can add their own.

---

@Author:        Claude Sonnet 4.6
@Created on:    08.04.2026
@Based on:      src/core/logger.ts

"""

import json
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class Logger:
    """Structured JSON logger with child-logger support.

    Args:
        bindings: Key-value pairs merged into every log record.
    """

    def __init__(self, bindings: Optional[dict[str, Any]] = None) -> None:
        self._bindings: dict[str, Any] = bindings or {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write(
        self,
        level: str,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        payload: dict[str, Any] = {
            "level": level,
            "time": datetime.now(tz=timezone.utc).isoformat(),
            "message": message,
            **self._bindings,
            **(data or {}),
        }
        line = json.dumps(payload, default=str)
        if level == "error":
            print(line, file=sys.stderr)
        elif level == "warn":
            print(line, file=sys.stderr)
        else:
            print(line)

    # ------------------------------------------------------------------
    # Public logging methods
    # ------------------------------------------------------------------

    def debug(
        self, message: str, data: Optional[dict[str, Any]] = None
    ) -> None:
        """Emit a DEBUG-level log record.

        Args:
            message: Human-readable log message.
            data: Optional extra key-value pairs to merge into the record.
        """
        self._write("debug", message, data)

    def info(
        self, message: str, data: Optional[dict[str, Any]] = None
    ) -> None:
        """Emit an INFO-level log record.

        Args:
            message: Human-readable log message.
            data: Optional extra key-value pairs to merge into the record.
        """
        self._write("info", message, data)

    def warn(
        self, message: str, data: Optional[dict[str, Any]] = None
    ) -> None:
        """Emit a WARN-level log record.

        Args:
            message: Human-readable log message.
            data: Optional extra key-value pairs to merge into the record.
        """
        self._write("warn", message, data)

    def error(
        self, message: str, data: Optional[dict[str, Any]] = None
    ) -> None:
        """Emit an ERROR-level log record.

        Args:
            message: Human-readable log message.
            data: Optional extra key-value pairs to merge into the record.
        """
        self._write("error", message, data)

    def child(self, bindings: dict[str, Any]) -> "Logger":
        """Create a child logger with additional bindings.

        Args:
            bindings: Extra key-value pairs to merge with parent bindings.

        Returns:
            A new ``Logger`` instance that inherits all parent bindings
            plus the supplied extras.
        """
        return Logger({**self._bindings, **bindings})


def create_logger(bindings: Optional[dict[str, Any]] = None) -> Logger:
    """Create a new root Logger instance.

    Args:
        bindings: Optional initial key-value pairs for every log record.

    Returns:
        A configured ``Logger`` instance.
    """
    return Logger(bindings or {})
