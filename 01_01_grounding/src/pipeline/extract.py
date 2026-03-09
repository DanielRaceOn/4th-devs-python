# -*- coding: utf-8 -*-

#   extract.py

"""
### Description:
Extract pipeline stage: calls the Responses API per paragraph to identify
concepts, caches results to concepts.json, and supports incremental updates.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `src/pipeline/extract.js`

"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from ..api import call_responses, parse_json_output
from ..config import paths, models, cli
from ..utils.file import ensure_dir, read_json_if_exists, safe_write_json
from ..utils.hash import hash_object, hash_text
from ..utils.text import chunk, get_paragraph_type, get_target_count
from ..schemas.extract import extract_schema
from ..prompts.extract import build_extract_prompt
from .concept_filter import filter_concepts

_CONCURRENCY = 5


def _update_concept_counts(concepts_data: dict[str, Any]) -> None:
    count = sum(len(p["concepts"]) for p in concepts_data["paragraphs"])
    concepts_data["paragraphCount"] = len(concepts_data["paragraphs"])
    concepts_data["conceptCount"] = count


def _compute_concepts_hash(concepts_data: dict[str, Any]) -> str:
    payload = [
        {
            "index": p["index"],
            "hash": p["hash"],
            "concepts": [
                {
                    "label": c["label"],
                    "category": c["category"],
                    "needsSearch": c["needsSearch"],
                    "searchQuery": c["searchQuery"],
                    "surfaceForms": c["surfaceForms"],
                }
                for c in p["concepts"]
            ],
        }
        for p in concepts_data["paragraphs"]
    ]
    return hash_object(payload)


async def _update_and_persist(
    concepts_data: dict[str, Any],
    entry_by_index: dict[int, dict[str, Any]],
    source_hash: str,
    current_indices: set[int],
) -> None:
    for key in list(entry_by_index.keys()):
        if key not in current_indices:
            del entry_by_index[key]

    concepts_data["paragraphs"] = sorted(entry_by_index.values(), key=lambda p: p["index"])
    _update_concept_counts(concepts_data)
    concepts_data["sourceHash"] = source_hash
    concepts_data["model"] = models["extract"]
    concepts_data["conceptsHash"] = _compute_concepts_hash(concepts_data)
    await safe_write_json(paths["concepts"], concepts_data)


def build_concept_entries(concepts_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten all concepts from all paragraphs into a single annotated list.

    Args:
        concepts_data: Parsed concepts.json data dict.

    Returns:
        List of concept dicts, each augmented with ``paragraphIndex``.
    """
    entries = []
    for paragraph in concepts_data["paragraphs"]:
        for concept in paragraph["concepts"]:
            entries.append({**concept, "paragraphIndex": paragraph["index"]})
    return entries


async def _extract_single_paragraph(item: dict[str, Any], total: int) -> dict[str, Any]:
    paragraph_type = get_paragraph_type(item["paragraph"])
    target_count = get_target_count(paragraph_type)

    input_text = build_extract_prompt(
        paragraph=item["paragraph"],
        paragraph_type=paragraph_type,
        target_count=target_count,
        index=item["index"],
        total=total,
    )

    data = await call_responses(
        model=models["extract"],
        input=input_text,
        text_format=extract_schema,
        reasoning={"effort": "medium"},
    )

    result = parse_json_output(data, f"extract: paragraph {item['index'] + 1}")
    filtered = filter_concepts(
        concepts=result.get("concepts") or [],
        paragraph=item["paragraph"],
        paragraph_type=paragraph_type,
    )

    return {
        "index": item["index"],
        "hash": item["hash"],
        "text": item["paragraph"],
        "concepts": filtered,
        "rawCount": len(result.get("concepts") or []),
    }


async def extract_concepts(
    paragraphs: list[str],
    source_file: Path,
) -> dict[str, Any]:
    """Extract concepts from all paragraphs, using cache where possible.

    Args:
        paragraphs: List of paragraph strings from the source markdown.
        source_file: Absolute path to the source markdown file.

    Returns:
        Populated ``conceptsData`` dict (also written to ``concepts.json``).
    """
    await ensure_dir(paths["output"])

    source_hash = hash_text("\n\n".join(paragraphs))
    existing = await read_json_if_exists(paths["concepts"])
    should_reuse = existing and existing.get("sourceFile") == str(source_file) and not cli["force"]
    same_source_hash = existing and existing.get("sourceHash") == source_hash
    same_model = existing and existing.get("model") == models["extract"]

    if should_reuse and same_source_hash and same_model:
        return existing

    concepts_data: dict[str, Any] = (
        existing
        if should_reuse
        else {"sourceFile": str(source_file), "model": models["extract"], "paragraphs": []}
    )

    entry_by_index: dict[int, dict[str, Any]] = {
        p["index"]: p for p in concepts_data["paragraphs"]
    }

    pending = []
    for index, paragraph in enumerate(paragraphs):
        paragraph_hash = hash_text(paragraph)
        cached = entry_by_index.get(index)
        if cached and cached.get("hash") == paragraph_hash and not cli["force"]:
            logging.debug("  [%d/%d] Cached", index + 1, len(paragraphs))
            continue
        pending.append({"index": index, "paragraph": paragraph, "hash": paragraph_hash})

    current_indices = set(range(len(paragraphs)))

    if not pending:
        await _update_and_persist(concepts_data, entry_by_index, source_hash, current_indices)
        return concepts_data

    batches = chunk(pending, _CONCURRENCY)
    logging.info("  Processing %d paragraphs (%d parallel)", len(pending), _CONCURRENCY)

    for batch_index, batch in enumerate(batches):
        indices_str = ", ".join(str(item["index"] + 1) for item in batch)
        logging.info(
            "  [batch %d/%d] Paragraphs: %s", batch_index + 1, len(batches), indices_str
        )

        results = await asyncio.gather(
            *[_extract_single_paragraph(item, len(paragraphs)) for item in batch]
        )

        for result in results:
            dropped = result["rawCount"] - len(result["concepts"])
            entry_by_index[result["index"]] = {
                "index": result["index"],
                "hash": result["hash"],
                "text": result["text"],
                "concepts": result["concepts"],
            }
            drop_info = f" (filtered {dropped})" if dropped > 0 else ""
            logging.info(
                "    ✓ [%d] %d concepts%s",
                result["index"] + 1,
                len(result["concepts"]),
                drop_info,
            )

        await _update_and_persist(concepts_data, entry_by_index, source_hash, current_indices)

    return concepts_data
