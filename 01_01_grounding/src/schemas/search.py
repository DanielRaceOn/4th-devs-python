# -*- coding: utf-8 -*-

#   search.py

"""
### Description:
JSON schema for web search result responses from the Responses API.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `src/schemas/search.js`

"""

from typing import Any

search_schema: dict[str, Any] = {
    "type": "json_schema",
    "name": "web_search_result",
    "strict": True,
    "schema": {
        "type": "object",
        "description": "Web search summary and sources for a single concept.",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Concise factual summary grounded in sources.",
            },
            "keyPoints": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
                "description": "2-4 concise bullet-like key points.",
            },
            "sources": {
                "type": "array",
                "minItems": 0,
                "description": "Cited sources from web search.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": ["string", "null"],
                            "description": "Optional page title.",
                        },
                        "url": {"type": "string", "description": "Source URL."},
                    },
                    "required": ["title", "url"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["summary", "keyPoints", "sources"],
        "additionalProperties": False,
    },
}
