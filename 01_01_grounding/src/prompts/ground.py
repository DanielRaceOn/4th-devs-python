# -*- coding: utf-8 -*-

#   ground.py

"""
### Description:
Prompt builder for the HTML grounding pipeline stage.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `src/prompts/ground.js`

"""

import json
from typing import Any


def build_ground_prompt(
    *,
    paragraph: str,
    grounding_items: list[dict[str, Any]],
    index: int,
    total: int,
) -> str:
    """Build the HTML grounding prompt for a single paragraph.

    Args:
        paragraph: Raw text of the paragraph to convert.
        grounding_items: List of dicts with ``label``, ``surfaceForms``, ``dataAttr``.
        index: Zero-based paragraph index.
        total: Total paragraph count.

    Returns:
        Formatted prompt string.
    """
    return (
        "Convert this single paragraph into semantic HTML.\n"
        "Highlight concepts by wrapping exact surfaceForms with:\n"
        '<span class="grounded" data-grounding="...">phrase</span>\n\n'
        "Rules:\n"
        "- Only wrap phrases that appear verbatim in the paragraph\n"
        "- Use the provided dataAttr value verbatim for data-grounding\n"
        "- Prefer the longest matching surfaceForm when multiple overlaps exist\n"
        "- Avoid wrapping the same concept multiple times\n"
        "- Do not add new facts. Preserve the original wording\n"
        "- Use appropriate HTML tags (h1-h6 for headers, p for paragraphs, ul/ol for lists)\n\n"
        "Return JSON only.\n\n"
        f"Document context: paragraph {index + 1} of {total}\n\n"
        f"Grounding items for this paragraph:\n{json.dumps(grounding_items, indent=2)}\n\n"
        f"--- Paragraph ---\n{paragraph}"
    )
