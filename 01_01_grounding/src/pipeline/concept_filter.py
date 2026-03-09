# -*- coding: utf-8 -*-

#   concept_filter.py

"""
### Description:
Concept normalisation and filtering: validates, deduplicates, and caps the list
of extracted concepts per paragraph before caching.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `src/pipeline/concept-filter.js`

"""

import re
from typing import Any

from ..schemas.categories import CONCEPT_CATEGORIES

MAX_BODY = 5
MAX_HEADER = 1
_MAX_SURFACE_FORM_LENGTH = 100


def _strip_markdown_syntax(text: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", text).strip()


def _normalize_surface_forms(surface_forms: Any, paragraph: str) -> list[str]:
    if not isinstance(surface_forms, list):
        return []

    clean_paragraph = _strip_markdown_syntax(paragraph)
    unique: dict[str, None] = {}

    for form in surface_forms:
        if not isinstance(form, str):
            continue
        trimmed = form.strip()
        if not trimmed:
            continue
        trimmed = _strip_markdown_syntax(trimmed)
        if not trimmed:
            continue
        if len(trimmed) > _MAX_SURFACE_FORM_LENGTH:
            continue
        if trimmed not in paragraph and trimmed not in clean_paragraph:
            continue
        unique[trimmed] = None

    return list(unique.keys())


def _normalize_concept(concept: Any, paragraph: str) -> dict[str, Any] | None:
    if not concept or not isinstance(concept, dict):
        return None

    label = concept.get("label", "")
    if not isinstance(label, str) or not label.strip():
        return None
    label = label.strip()

    raw_category = concept.get("category", "")
    category = raw_category.strip().lower() if isinstance(raw_category, str) else "concept"
    if category not in CONCEPT_CATEGORIES:
        category = "concept"

    needs_search = bool(concept.get("needsSearch"))
    raw_query = concept.get("searchQuery")
    search_query = raw_query.strip() if isinstance(raw_query, str) and raw_query.strip() else None

    if not needs_search:
        search_query = None
    elif not search_query:
        search_query = label

    raw_reason = concept.get("reason", "")
    reason = raw_reason.strip() if isinstance(raw_reason, str) else ""
    surface_forms = _normalize_surface_forms(concept.get("surfaceForms"), paragraph)

    if not surface_forms:
        return None

    return {
        "label": label,
        "category": category,
        "needsSearch": needs_search,
        "searchQuery": search_query,
        "reason": reason,
        "surfaceForms": surface_forms,
    }


def filter_concepts(
    *,
    concepts: list[Any],
    paragraph: str,
    paragraph_type: str,
) -> list[dict[str, Any]]:
    """Normalize, deduplicate, and cap concepts for a single paragraph.

    Args:
        concepts: Raw concept list from the API response.
        paragraph: Original paragraph text (used for surface-form validation).
        paragraph_type: ``'header'`` or ``'body'`` (controls max count).

    Returns:
        Filtered and capped list of normalized concept dicts.
    """
    max_count = MAX_HEADER if paragraph_type == "header" else MAX_BODY

    if not isinstance(concepts, list):
        return []

    normalized = [_normalize_concept(c, paragraph) for c in concepts]
    valid = [c for c in normalized if c is not None]

    deduped: dict[str, dict[str, Any]] = {}
    for concept in valid:
        if concept["label"] not in deduped:
            deduped[concept["label"]] = concept

    sorted_concepts = sorted(deduped.values(), key=lambda c: len(c["label"]), reverse=True)
    return sorted_concepts[:max_count]
