# -*- coding: utf-8 -*-

#   ground.py

"""
### Description:
HTML grounding pipeline stage: converts each paragraph into semantic HTML with
concept-annotated spans, then inserts the result into the HTML template.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `src/pipeline/ground.js`

"""

import asyncio
import html
import json
import logging
import re
from typing import Any

from ..api import call_responses, parse_json_output
from ..config import paths, models
from ..utils.file import ensure_dir
from ..utils.text import chunk, split_paragraphs, truncate
from ..schemas.ground import ground_schema
from ..prompts.ground import build_ground_prompt
from .extract import build_concept_entries

_CONCURRENCY = 5


def _escape_attribute(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _build_grounding_items(
    concepts_data: dict[str, Any],
    dedupe_data: dict[str, Any],
    search_data: dict[str, Any],
) -> list[dict[str, Any]]:
    concept_entries = [
        {"id": idx, **c}
        for idx, c in enumerate(build_concept_entries(concepts_data))
        if c.get("needsSearch")
    ]
    entry_by_id = {e["id"]: e for e in concept_entries}

    items = []
    for group in dedupe_data["groups"]:
        members = [entry_by_id[i] for i in group["ids"] if i in entry_by_id]
        surface_forms = [sf for m in members for sf in (m.get("surfaceForms") or [])]
        paragraph_indices = list({m["paragraphIndex"] for m in members})

        search_result = search_data["resultsByCanonical"].get(group["canonical"]) or {}
        sources = [
            {"title": s.get("title"), "url": s["url"]}
            for s in (search_result.get("sources") or [])
            if s.get("url")
        ]

        summary = truncate(search_result.get("summary") or "", 420)
        data_attr = _escape_attribute(json.dumps({"summary": summary, "sources": sources}))

        items.append(
            {
                "label": group["canonical"],
                "surfaceForms": sorted(list(dict.fromkeys(surface_forms)), key=len, reverse=True),
                "paragraphIndices": paragraph_indices,
                "dataAttr": data_attr,
            }
        )
    return items


def _convert_to_basic_html(paragraph: str) -> str:
    trimmed = paragraph.strip()

    header_match = re.match(r"^(#{1,6})\s+(.+)$", trimmed)
    if header_match:
        level = len(header_match.group(1))
        text = header_match.group(2)
        return f"<h{level}>{_escape_html(text)}</h{level}>"

    if re.search(r"^[-*]\s+", trimmed, re.MULTILINE):
        items_html = "\n".join(
            f"<li>{_escape_html(line.lstrip('-* ').strip())}</li>"
            for line in trimmed.splitlines()
            if re.match(r"^[-*]\s+", line)
        )
        return f"<ul>\n{items_html}\n</ul>"

    return f"<p>{_escape_html(trimmed)}</p>"


async def _ground_single_paragraph(
    paragraph: str,
    relevant_items: list[dict[str, Any]],
    index: int,
    total: int,
) -> str:
    if not relevant_items:
        return _convert_to_basic_html(paragraph)

    input_text = build_ground_prompt(
        paragraph=paragraph,
        grounding_items=[
            {"label": item["label"], "surfaceForms": item["surfaceForms"], "dataAttr": item["dataAttr"]}
            for item in relevant_items
        ],
        index=index,
        total=total,
    )

    data = await call_responses(
        model=models["ground"],
        input=input_text,
        text_format=ground_schema,
        reasoning={"effort": "medium"},
    )
    result = parse_json_output(data, f"ground: paragraph {index + 1}")
    return result["html"]


async def generate_and_apply_template(
    markdown: str,
    concepts_data: dict[str, Any],
    dedupe_data: dict[str, Any],
    search_data: dict[str, Any],
) -> str:
    """Ground all paragraphs and write the final HTML to the output file.

    Args:
        markdown: Raw markdown source text.
        concepts_data: Output from ``extract_concepts``.
        dedupe_data: Output from ``dedupe_concepts``.
        search_data: Output from ``search_concepts``.

    Returns:
        Absolute path string of the written grounded HTML file.

    Raises:
        RuntimeError: If the template is missing the ``<!--CONTENT-->`` placeholder.
    """
    grounding_items = _build_grounding_items(concepts_data, dedupe_data, search_data)
    paragraphs = split_paragraphs(markdown)
    total = len(paragraphs)

    logging.info("   Processing %d paragraphs (%d parallel)", total, _CONCURRENCY)
    batches = chunk(
        [{"paragraph": p, "index": i} for i, p in enumerate(paragraphs)],
        _CONCURRENCY,
    )

    html_parts: list[str] = [""] * total

    for batch_index, batch in enumerate(batches):
        indices_str = ", ".join(str(item["index"] + 1) for item in batch)
        logging.info(
            "  [batch %d/%d] Paragraphs: %s", batch_index + 1, len(batches), indices_str
        )

        results = await asyncio.gather(
            *[
                _ground_single_paragraph(
                    item["paragraph"],
                    [gi for gi in grounding_items if item["index"] in gi["paragraphIndices"]],
                    item["index"],
                    total,
                )
                for item in batch
            ]
        )

        for i, result in enumerate(results):
            idx = batch[i]["index"]
            html_parts[idx] = result
            logging.info("    ✓ [%d] grounded", idx + 1)

    html_chunk = "\n\n".join(html_parts)
    template = paths["template"].read_text(encoding="utf-8")

    if "<!--CONTENT-->" not in template:
        raise RuntimeError("Template is missing <!--CONTENT--> placeholder.")

    filled = template.replace("<!--CONTENT-->", html_chunk)

    await ensure_dir(paths["output"])
    paths["grounded"].write_text(filled, encoding="utf-8")

    return str(paths["grounded"])
