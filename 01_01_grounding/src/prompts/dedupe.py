# -*- coding: utf-8 -*-

#   dedupe.py

"""
### Description:
Prompt builder for the concept deduplication pipeline stage.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `src/prompts/dedupe.js`

"""

import json
from typing import Any


def build_dedupe_prompt(*, concept_entries: list[dict[str, Any]]) -> str:
    """Build the deduplication prompt for a list of concept entries.

    Args:
        concept_entries: List of concept dicts, each with an ``id`` field.

    Returns:
        Formatted prompt string.
    """
    return (
        "Group concepts only when they are strict paraphrases of the same claim or term.\n"
        "Do NOT group related-but-distinct ideas "
        "(cause/effect, property vs consequence, part/whole, example vs category, "
        "metric vs definition).\n"
        "Only group items with the same category; if categories differ, keep them separate "
        "even if similar.\n"
        "Every id must appear in exactly one group.\n"
        "Pick a concise canonical label that preserves the full meaning.\n"
        "aliases must be full alternative labels, not fragments or partial phrases.\n"
        "If unsure, do not group.\n"
        "Return JSON only.\n"
        f"<concepts>\n{json.dumps(concept_entries, indent=2)}\n</concepts>\n"
    )
