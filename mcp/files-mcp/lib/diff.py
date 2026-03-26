# -*- coding: utf-8 -*-

#   diff.py

"""
### Description:
Unified diff generation helper.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

import difflib


def make_diff(original_lines: list[str], new_lines: list[str]) -> str:
    """Produce a unified-style diff between two line lists.

    Args:
        original_lines: Lines before the change.
        new_lines: Lines after the change.

    Returns:
        Diff string with ``-`` / ``+`` prefixes, or empty string if no changes.
    """
    return "\n".join(difflib.unified_diff(original_lines, new_lines, lineterm="", n=2))
