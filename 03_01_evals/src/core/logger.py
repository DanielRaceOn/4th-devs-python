# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
JSON structured logger — mirrors src/core/logger.ts.

Provides a ``Logger`` class with ``debug``, ``info``, ``warn``, and
``error`` methods that emit JSON lines to stdout, and a ``child``
method that merges additional bindings into every subsequent message.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/core/logger.ts

"""

import json
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class Logger:
    """Structured JSON logger with child-binding support."""

    def __init__(self, bindings: Optional[dict[str, Any]] = None) -> None:
        self._bindings: dict[str, Any] = bindings or {}

    def _emit(self, level: str, message: str, data: Optional[dict[str, Any]] = None) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "level": level,
            "msg": message,
            **self._bindings,
            **(data or {}),
        }
        print(json.dumps(record), file=sys.stdout)

    def debug(self, message: str, data: Optional[dict[str, Any]] = None) -> None:
        """Emit a DEBUG-level log line.

        Args:
            message: Log message.
            data: Optional extra fields to include.
        """
        self._emit("debug", message, data)

    def info(self, message: str, data: Optional[dict[str, Any]] = None) -> None:
        """Emit an INFO-level log line.

        Args:
            message: Log message.
            data: Optional extra fields to include.
        """
        self._emit("info", message, data)

    def warn(self, message: str, data: Optional[dict[str, Any]] = None) -> None:
        """Emit a WARN-level log line.

        Args:
            message: Log message.
            data: Optional extra fields to include.
        """
        self._emit("warn", message, data)

    def error(self, message: str, data: Optional[dict[str, Any]] = None) -> None:
        """Emit an ERROR-level log line.

        Args:
            message: Log message.
            data: Optional extra fields to include.
        """
        self._emit("error", message, data)

    def child(self, bindings: dict[str, Any]) -> "Logger":
        """Create a child logger with additional fixed bindings.

        Args:
            bindings: Key-value pairs merged into every log record.

        Returns:
            A new ``Logger`` instance with merged bindings.
        """
        return Logger({**self._bindings, **bindings})


def create_logger(bindings: Optional[dict[str, Any]] = None) -> Logger:
    """Construct a root logger with optional initial bindings.

    Args:
        bindings: Optional initial key-value pairs for every log record.

    Returns:
        A configured ``Logger`` instance.
    """
    return Logger(bindings)
