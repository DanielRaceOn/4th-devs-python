# -*- coding: utf-8 -*-

#   lines.py

"""
### Description:
Line parsing, numbering, and range helpers.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

import re

_RANGE_RE = re.compile(r"^\d+(-\d+)?$")


def parse_line_range(spec: str, total: int) -> tuple[int, int] | str:
    """Parse a line range spec into (start, end) 0-based indices (inclusive).

    If start > end after parsing, the range is inverted (unusual but not rejected —
    callers receive an empty or reversed slice).

    Args:
        spec: A string like ``"10"`` or ``"10-50"``. Must match ``^\\d+(-\\d+)?$``.
              Negative numbers (e.g. ``"-5"``) are rejected.
        total: Total number of lines in the file.

    Returns:
        Tuple of (start_index, end_index) 0-based, clamped to [0, total-1],
        or an error string if the spec is invalid.
    """
    spec = spec.strip()
    if not _RANGE_RE.match(spec):
        return f"Invalid line range: {spec!r}. Expected format: '10' or '10-50'."

    if "-" in spec:
        parts = spec.split("-", 1)
        start = int(parts[0]) - 1
        end = int(parts[1]) - 1
    else:
        start = int(spec) - 1
        end = start

    start = max(0, start)
    end = min(total - 1, end)
    return start, end


def add_line_numbers(lines: list[str], offset: int = 0) -> str:
    """Format lines with 1-based line numbers.

    Args:
        lines: List of text lines.
        offset: Added to the 1-based index so numbers reflect the original file
                position when slicing (e.g. pass ``start`` from ``parse_line_range``).

    Returns:
        Newline-joined string with ``{n}|{line}`` format.
    """
    return "\n".join(f"{i + offset + 1}|{line}" for i, line in enumerate(lines))
