# -*- coding: utf-8 -*-

#   text.py

"""
### Description:
Text processing utilities: paragraph splitting, chunking, truncation,
and paragraph-type classification used across the grounding pipeline.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `src/utils/text.js`

"""

import re
from typing import TypeVar

from ..pipeline.concept_filter import MAX_BODY, MAX_HEADER

T = TypeVar("T")


def split_paragraphs(markdown: str) -> list[str]:
    """Split markdown text into non-empty paragraphs.

    Args:
        markdown: Raw markdown string.

    Returns:
        List of trimmed, non-empty paragraph strings.
    """
    text = markdown.replace("\r\n", "\n")
    blocks = re.split(r"\n\s*\n+", text)
    return [block.strip() for block in blocks if block.strip()]


def chunk(items: list[T], size: int) -> list[list[T]]:
    """Split a list into consecutive chunks of at most ``size`` elements.

    Args:
        items: List to split.
        size: Maximum chunk size.

    Returns:
        List of sub-lists.
    """
    count = (len(items) + size - 1) // size
    return [items[i * size : i * size + size] for i in range(count)]


def truncate(text: str, max_len: int) -> str:
    """Truncate ``text`` to at most ``max_len`` characters.

    Args:
        text: Input string.
        max_len: Maximum allowed length.

    Returns:
        Original string if short enough, otherwise truncated with ``...``.
    """
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def get_paragraph_type(paragraph: str) -> str:
    """Classify a paragraph as ``'header'`` or ``'body'``.

    Args:
        paragraph: Single paragraph string.

    Returns:
        ``'header'`` if the paragraph starts with ``#``, else ``'body'``.
    """
    return "header" if re.match(r"^#{1,6}\s+", paragraph) else "body"


def get_target_count(paragraph_type: str) -> str:
    """Return the target concept count range string for extraction prompts.

    Args:
        paragraph_type: Either ``'header'`` or ``'body'``.

    Returns:
        String like ``'0-1'`` or ``'2-5'``.
    """
    return f"0-{MAX_HEADER}" if paragraph_type == "header" else f"2-{MAX_BODY}"
