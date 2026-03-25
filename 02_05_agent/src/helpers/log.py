# -*- coding: utf-8 -*-

#   log.py

"""
### Description:
Tagged logger helpers for the 02_05_agent module.

Provides `log()` and `log_error()` functions that prefix messages with a
subsystem tag (agent, memory, observer, reflector, flush, session) so
console output is easy to scan during a demo run.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/helpers/log.ts


"""

from typing import Literal, Optional

from .utils import format_error  # noqa: F401 — re-exported for callers that import from here

Tag = Literal["agent", "memory", "observer", "reflector", "flush", "session"]


def _prefix(tag: Tag) -> str:
    """Return the log prefix string for *tag*, e.g. ``'  [agent]'``."""
    return f"  [{tag}]"


def log(tag: Tag, message: str) -> None:
    """Print a tagged info message to stdout.

    Args:
        tag: Subsystem identifier.
        message: Human-readable log message.
    """
    print(f"{_prefix(tag)} {message}")


def log_error(tag: Tag, message: str, err: Optional[BaseException] = None) -> None:
    """Print a tagged error message to stderr.

    Args:
        tag: Subsystem identifier.
        message: Human-readable error description.
        err: Optional exception whose message is appended.
    """
    import sys

    if err is not None:
        print(f"{_prefix(tag)} {message} {format_error(err)}", file=sys.stderr)
    else:
        print(f"{_prefix(tag)} {message}", file=sys.stderr)


