# -*- coding: utf-8 -*-

#   utils.py

"""
### Description:
General-purpose utility helpers for the 02_05_agent module.

Provides string truncation, XML tag extraction, JSON argument parsing,
and error formatting used across multiple subsystems.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/helpers/utils.ts


"""

import json
import re
from typing import Any, Optional


def truncate(s: str, max_len: int = 100) -> str:
    """Truncate a string to at most ``max_len`` characters.

    Args:
        s: Input string.
        max_len: Maximum allowed length (default 100).

    Returns:
        The original string, or a truncated version ending with ``…``.
    """
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def extract_tag(text: str, tag: str) -> Optional[str]:
    """Extract the inner text of the first matching XML-style tag.

    Args:
        text: Source text containing XML-style tags.
        tag: Tag name to search for (case-insensitive).

    Returns:
        Stripped inner content, or ``None`` if the tag is not found.
    """
    pattern = rf"<{re.escape(tag)}>([\s\S]*?)</{re.escape(tag)}>"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        inner = match.group(1).strip()
        return inner if inner else None
    return None


def parse_args(raw: str) -> dict[str, Any]:
    """Parse a JSON object string into a Python dict.

    Args:
        raw: JSON-encoded string (may be empty, defaults to ``{}``).

    Returns:
        Parsed dict.

    Raises:
        ValueError: If the parsed value is not a JSON object.
    """
    parsed: Any = json.loads(raw or "{}")
    if not isinstance(parsed, dict):
        kind = "array" if isinstance(parsed, list) else type(parsed).__name__
        raise ValueError(f"Expected JSON object, got {kind}")
    return parsed


def format_error(err: BaseException) -> str:
    """Return a concise string representation of an exception.

    Args:
        err: Any exception.

    Returns:
        The exception message string.
    """
    return str(err)
