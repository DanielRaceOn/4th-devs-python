# -*- coding: utf-8 -*-

#   hash.py

"""
### Description:
Deterministic hashing utilities for text and objects.
Mirrors the JS stable-stringify approach for consistent cross-run hashes.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `src/utils/hash.js`

"""

import hashlib
import json
from typing import Any


def _stable_stringify(value: Any) -> str:
    """Produce a deterministic JSON-like string for any value.

    Object keys are sorted at every level so the output is stable across runs.

    Args:
        value: Any JSON-serialisable value.

    Returns:
        Deterministic string representation.
    """
    if isinstance(value, list):
        return "[" + ",".join(_stable_stringify(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys())
        entries = [f"{json.dumps(k)}:{_stable_stringify(value[k])}" for k in keys]
        return "{" + ",".join(entries) + "}"
    return json.dumps(value)


def hash_text(text: str) -> str:
    """Return the SHA-256 hex digest of ``text``.

    Args:
        text: Input string to hash.

    Returns:
        64-character hex string.
    """
    return hashlib.sha256(text.encode()).hexdigest()


def hash_object(obj: Any) -> str:
    """Return the SHA-256 hex digest of a stably-stringified object.

    Args:
        obj: Any JSON-serialisable value.

    Returns:
        64-character hex string.
    """
    return hash_text(_stable_stringify(obj))
