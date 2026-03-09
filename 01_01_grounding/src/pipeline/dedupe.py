# -*- coding: utf-8 -*-

#   dedupe.py

"""
### Description:
Deduplicate pipeline stage: groups synonymous concepts under canonical labels
using the Responses API, caches results to dedupe.json.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `src/pipeline/dedupe.js`

"""

import logging
from typing import Any

from ..api import call_responses, parse_json_output
from ..config import paths, models, cli
from ..utils.file import read_json_if_exists, safe_write_json
from ..utils.hash import hash_object
from ..schemas.dedupe import dedupe_schema
from ..prompts.dedupe import build_dedupe_prompt
from .extract import build_concept_entries


async def dedupe_concepts(concepts_data: dict[str, Any]) -> dict[str, Any]:
    """Group synonymous concepts under canonical labels.

    Reads ``concepts.json`` cache; skips the API call if nothing changed.

    Args:
        concepts_data: Output from ``extract_concepts``.

    Returns:
        Populated ``dedupeData`` dict (also written to ``dedupe.json``).
    """
    existing = await read_json_if_exists(paths["dedupe"])
    same_source = existing and existing.get("sourceFile") == concepts_data.get("sourceFile")
    same_counts = (
        existing
        and existing.get("paragraphCount") == concepts_data.get("paragraphCount")
        and existing.get("conceptCount") == concepts_data.get("conceptCount")
    )
    same_source_hash = existing and existing.get("sourceHash") == concepts_data.get("sourceHash")
    same_concepts_hash = (
        existing and existing.get("conceptsHash") == concepts_data.get("conceptsHash")
    )

    if same_source and same_counts and same_source_hash and same_concepts_hash and not cli["force"]:
        logging.debug("   Using cached dedupe data")
        if not existing.get("dedupeHash"):
            existing["dedupeHash"] = hash_object(existing.get("groups") or [])
            await safe_write_json(paths["dedupe"], existing)
        return existing

    concept_entries = [
        {"id": idx, **concept}
        for idx, concept in enumerate(build_concept_entries(concepts_data))
        if concept.get("needsSearch")
    ]

    if not concept_entries:
        empty: dict[str, Any] = {
            "sourceFile": concepts_data.get("sourceFile"),
            "model": models["extract"],
            "sourceHash": concepts_data.get("sourceHash"),
            "conceptsHash": concepts_data.get("conceptsHash"),
            "paragraphCount": concepts_data.get("paragraphCount"),
            "conceptCount": concepts_data.get("conceptCount"),
            "dedupeHash": hash_object([]),
            "groups": [],
        }
        await safe_write_json(paths["dedupe"], empty)
        return empty

    input_text = build_dedupe_prompt(concept_entries=concept_entries)
    data = await call_responses(
        model=models["extract"],
        input=input_text,
        text_format=dedupe_schema,
        reasoning={"effort": "medium"},
    )
    result = parse_json_output(data, "concept dedupe")

    dedupe_data: dict[str, Any] = {
        "sourceFile": concepts_data.get("sourceFile"),
        "model": models["extract"],
        "sourceHash": concepts_data.get("sourceHash"),
        "conceptsHash": concepts_data.get("conceptsHash"),
        "paragraphCount": concepts_data.get("paragraphCount"),
        "conceptCount": concepts_data.get("conceptCount"),
        "dedupeHash": hash_object(result["groups"]),
        "groups": result["groups"],
    }

    await safe_write_json(paths["dedupe"], dedupe_data)
    return dedupe_data
