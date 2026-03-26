# -*- coding: utf-8 -*-

#   checksum.py

"""
### Description:
SHA-256 checksum helpers — matching the JS server's checksum algorithm.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

import hashlib
from pathlib import Path


def checksum_file(path: Path) -> str:
    """Return a 12-char SHA-256 hex digest of file text (UTF-8).

    Matches the JS implementation: ``sha256(text, 'utf-8').slice(0, 12)``.

    Args:
        path: Absolute path to file.

    Returns:
        First 12 characters of the SHA-256 hex digest.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def checksum_text(text: str) -> str:
    """Return a 12-char SHA-256 hex digest of a text string.

    Args:
        text: String to hash.

    Returns:
        First 12 characters of the SHA-256 hex digest.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
