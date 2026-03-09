# -*- coding: utf-8 -*-

#   extract.py

"""
### Description:
JSON schema for concept extraction responses from the Responses API.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `src/schemas/extract.js`

"""

from typing import Any

from .categories import CONCEPT_CATEGORIES

extract_schema: dict[str, Any] = {
    "type": "json_schema",
    "name": "concept_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "description": "Extracted concepts from a single paragraph.",
        "properties": {
            "concepts": {
                "type": "array",
                "description": (
                    "Extracted claims and terms for this paragraph. Each surfaceForm should be "
                    "a short key phrase (3-12 words), not a full sentence. "
                    "Empty array if nothing qualifies."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "Canonical name for the claim or term being extracted.",
                        },
                        "category": {
                            "type": "string",
                            "enum": CONCEPT_CATEGORIES,
                            "description": "Concept category from the allowed taxonomy.",
                        },
                        "needsSearch": {
                            "type": "boolean",
                            "description": (
                                "True when verification or extra context would help via web search."
                            ),
                        },
                        "searchQuery": {
                            "type": ["string", "null"],
                            "description": (
                                "Search query to verify/expand this concept. "
                                "Null if needsSearch is false."
                            ),
                        },
                        "reason": {
                            "type": "string",
                            "description": "Brief justification for why this concept was extracted.",
                        },
                        "surfaceForms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "description": (
                                "Short key phrases (3-12 words) copied exactly from the paragraph. "
                                "NOT entire sentences. "
                                "Never include markdown syntax like # or ##."
                            ),
                        },
                    },
                    "required": [
                        "label",
                        "category",
                        "needsSearch",
                        "searchQuery",
                        "reason",
                        "surfaceForms",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["concepts"],
        "additionalProperties": False,
    },
}
