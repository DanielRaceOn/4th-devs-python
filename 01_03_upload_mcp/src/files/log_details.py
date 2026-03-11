# -*- coding: utf-8 -*-

#   log_details.py

"""
### Description:
Logging helpers for file upload and read operations.
Shows previews of uploaded file content and first lines of read files
so the user can verify what the agent is doing.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/files/log-details.js`

"""

import base64
from typing import Any

from ..helpers.logger import log


def _decode_preview(b64: str, max_len: int = 80) -> str:
    """Decode a base64 string and return a truncated UTF-8 preview."""
    try:
        decoded = base64.b64decode(b64).decode("utf-8", errors="replace")
        return decoded[:max_len] + "…" if len(decoded) > max_len else decoded
    except Exception:
        return "[binary]"


def log_upload_details(args: dict) -> None:
    """Log a preview of each file being uploaded.

    Args:
        args: Tool arguments dict; looks for a ``files`` list.
    """
    files = args.get("files") or []
    for file in files:
        preview = _decode_preview(file.get("base64", ""))
        log.info(f"  📤 {file.get('name')} ({file.get('type')}) — {preview}")


def log_read_details(result: Any) -> None:
    """Log the first line of a read file result.

    Args:
        result: Tool result dict; looks for ``content.text``.
    """
    if not isinstance(result, dict):
        return
    text = (result.get("content") or {}).get("text", "")
    if not text:
        return
    first_line = text.split("\n")[0].replace(r"^\d+\|", "").strip()
    if first_line:
        log.info(f"  📥 {first_line}")
