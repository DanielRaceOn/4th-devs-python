# -*- coding: utf-8 -*-

#   ground.py

"""
### Description:
JSON schema for grounded paragraph HTML responses from the Responses API.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `src/schemas/ground.js`

"""

from typing import Any

ground_schema: dict[str, Any] = {
    "type": "json_schema",
    "name": "grounded_paragraph",
    "strict": True,
    "schema": {
        "type": "object",
        "description": "HTML output for a single grounded paragraph.",
        "properties": {
            "html": {
                "type": "string",
                "description": "HTML fragment for this paragraph with grounded spans.",
            }
        },
        "required": ["html"],
        "additionalProperties": False,
    },
}
