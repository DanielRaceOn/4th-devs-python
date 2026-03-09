# -*- coding: utf-8 -*-

#   search.py

"""
### Description:
Prompt builder for the web search grounding pipeline stage.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `src/prompts/search.js`

"""

from typing import Any


def build_search_prompt(*, concept: dict[str, Any]) -> str:
    """Build the web search prompt for a single canonical concept.

    Args:
        concept: Dict with ``canonical``, optional ``searchQuery``, and
            optional ``aliases`` list.

    Returns:
        Formatted prompt string.
    """
    prompt = (
        "Use web search to verify and expand on this concept.\n"
        "Search thoroughly and provide accurate, factual information.\n"
        "Return JSON only, matching the schema.\n\n"
        "Requirements:\n"
        "- Write a concise summary grounded in search results\n"
        "- Include 2-4 key points with specific facts\n"
        "- List sources with titles and URLs from the search\n\n"
        f"Concept: {concept['canonical']}"
    )

    if concept.get("searchQuery"):
        prompt += f"\nSearch query: {concept['searchQuery']}"

    aliases = concept.get("aliases") or []
    if aliases:
        prompt += f"\nAlso known as: {', '.join(aliases)}"

    return prompt
