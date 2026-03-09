# -*- coding: utf-8 -*-

#   search.py

"""
### Description:
Web search grounding pipeline stage: searches one API call per canonical concept,
caches results to search_results.json, and supports OpenRouter's :online model variant.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `src/pipeline/search.js`

"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from config import AI_PROVIDER  # noqa: E402

from ..api import call_responses, parse_json_output, get_web_sources  # noqa: E402
from ..config import paths, models, cli  # noqa: E402
from ..utils.file import read_json_if_exists, safe_write_json  # noqa: E402
from ..utils.text import chunk  # noqa: E402
from ..schemas.search import search_schema  # noqa: E402
from ..prompts.search import build_search_prompt  # noqa: E402
from .extract import build_concept_entries  # noqa: E402

_CONCURRENCY = 5
_OPENROUTER_ONLINE_SUFFIX = ":online"
_OPENAI_SEARCH_INCLUDE = ["web_search_call.action.sources"]


def _resolve_search_model() -> str:
    if AI_PROVIDER != "openrouter":
        return models["search"]
    if models["search"].endswith(_OPENROUTER_ONLINE_SUFFIX):
        return models["search"]
    return f"{models['search']}{_OPENROUTER_ONLINE_SUFFIX}"


def _build_search_request(*, model: str, input_text: str) -> dict[str, Any]:
    if AI_PROVIDER == "openrouter":
        return {"model": model, "input": input_text, "text_format": search_schema}
    return {
        "model": model,
        "input": input_text,
        "tools": [{"type": "web_search"}],
        "include": _OPENAI_SEARCH_INCLUDE,
        "text_format": search_schema,
    }


async def _search_single_concept(
    concept: dict[str, Any], model: str
) -> dict[str, Any]:
    input_text = build_search_prompt(concept=concept)
    request = _build_search_request(model=model, input_text=input_text)

    data = await call_responses(**request)
    result = parse_json_output(data, f"search: {concept['canonical']}")
    sources = get_web_sources(data)

    return {"canonical": concept["canonical"], **result, "rawSources": sources}


async def search_concepts(
    concepts_data: dict[str, Any],
    dedupe_data: dict[str, Any],
) -> dict[str, Any]:
    """Search the web for each canonical concept group.

    Reads ``search_results.json`` cache; re-searches only new or invalidated concepts.

    Args:
        concepts_data: Output from ``extract_concepts``.
        dedupe_data: Output from ``dedupe_concepts``.

    Returns:
        Populated ``searchData`` dict (also written to ``search_results.json``).
    """
    search_model = _resolve_search_model()

    if AI_PROVIDER == "openrouter":
        logging.warning(
            "   Using OpenRouter provider with web plugin via model: %s", search_model
        )

    existing = await read_json_if_exists(paths["search"])
    should_reuse = (
        existing
        and existing.get("sourceFile") == concepts_data.get("sourceFile")
        and not cli["force"]
    )
    same_source_hash = existing and existing.get("sourceHash") == concepts_data.get("sourceHash")
    same_dedupe_hash = existing and existing.get("dedupeHash") == dedupe_data.get("dedupeHash")
    same_model = existing and existing.get("model") == search_model

    should_reset = not same_source_hash or not same_dedupe_hash or not same_model

    if should_reuse and should_reset:
        logging.info("   Search cache invalidated (source, dedupe, or model changed)")

    if should_reuse and not should_reset:
        base = existing
        if not base.get("sourceHash"):
            base["sourceHash"] = concepts_data.get("sourceHash")
        if not base.get("dedupeHash"):
            base["dedupeHash"] = dedupe_data.get("dedupeHash")
    else:
        base = {
            "sourceFile": concepts_data.get("sourceFile"),
            "model": search_model,
            "sourceHash": concepts_data.get("sourceHash"),
            "dedupeHash": dedupe_data.get("dedupeHash"),
            "resultsByCanonical": {},
        }

    concept_entries = [
        {"id": idx, **concept}
        for idx, concept in enumerate(build_concept_entries(concepts_data))
        if concept.get("needsSearch")
    ]
    concept_by_id = {entry["id"]: entry for entry in concept_entries}

    canonical_concepts = []
    for group in dedupe_data["groups"]:
        member_entries = [concept_by_id[i] for i in group["ids"] if i in concept_by_id]
        search_query = next(
            (e["searchQuery"] for e in member_entries if e.get("searchQuery")),
            group["canonical"],
        )
        surface_forms = [sf for e in member_entries for sf in (e.get("surfaceForms") or [])]
        canonical_concepts.append(
            {
                "canonical": group["canonical"],
                "aliases": group["aliases"],
                "searchQuery": search_query,
                "surfaceForms": list(dict.fromkeys(surface_forms)),
            }
        )

    pending = [
        c for c in canonical_concepts if c["canonical"] not in base["resultsByCanonical"]
    ]

    if not pending and same_source_hash and same_dedupe_hash:
        logging.debug("   Using cached search results")
        return base

    logging.info("   %d concepts to search (%d parallel)", len(pending), _CONCURRENCY)
    batches = chunk(pending, _CONCURRENCY)

    for batch_index, batch in enumerate(batches):
        if not batch:
            continue
        batch_labels = ", ".join(c["canonical"] for c in batch)
        logging.info(
            "  [batch %d/%d] Searching: %s", batch_index + 1, len(batches), batch_labels
        )

        results = await asyncio.gather(
            *[_search_single_concept(concept, search_model) for concept in batch]
        )

        for result in results:
            base["resultsByCanonical"][result["canonical"]] = {
                "canonical": result["canonical"],
                "summary": result.get("summary"),
                "keyPoints": result.get("keyPoints"),
                "sources": result.get("sources"),
            }
            logging.info(
                "    ✓ %s (%d sources)",
                result["canonical"],
                len(result.get("sources") or []),
            )

        await safe_write_json(paths["search"], base)

    return base
