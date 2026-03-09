# -*- coding: utf-8 -*-

#   dedupe.py

"""
### Description:
JSON schema for concept deduplication responses from the Responses API.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `src/schemas/dedupe.js`

"""

from typing import Any

dedupe_schema: dict[str, Any] = {
    "type": "json_schema",
    "name": "concept_dedupe",
    "strict": True,
    "schema": {
        "type": "object",
        "description": "Groups of equivalent or near-equivalent concepts.",
        "properties": {
            "groups": {
                "type": "array",
                "description": "Each group clusters concept ids that refer to the same idea.",
                "minItems": 0,
                "items": {
                    "type": "object",
                    "description": "A single deduplicated concept group.",
                    "properties": {
                        "canonical": {
                            "type": "string",
                            "description": "Preferred canonical label for the group.",
                        },
                        "ids": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 1,
                            "description": "Ids of concept entries belonging to this group.",
                        },
                        "aliases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Alternative labels that map to the canonical concept.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Short justification for grouping.",
                        },
                    },
                    "required": ["canonical", "ids", "aliases", "rationale"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["groups"],
        "additionalProperties": False,
    },
}
