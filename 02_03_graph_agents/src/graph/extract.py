# -*- coding: utf-8 -*-

#   extract.py

"""
### Description:
Entity and relationship extraction from text chunks using an LLM.
Post-processing normalizes names, enforces allowed types, removes self-
referential edges, and deduplicates across chunks globally.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/graph/extract.js`

"""

import json
import re
import sys

from ..helpers.api import chat, extract_text
from ..helpers.logger import log

# ── Allowed enum sets ─────────────────────────────────────────────────────────

ENTITY_TYPES = {"concept", "person", "technology", "organization", "technique", "other"}

RELATIONSHIP_TYPES = {
    "relates_to", "uses", "part_of", "created_by",
    "influences", "contrasts_with", "example_of", "depends_on",
}

# ── Canonical name normalization ──────────────────────────────────────────────

# Note: JS original stores "LLMs" and "CoT" (mixed-case) but tests with
# word.toUpperCase(), so those two entries never actually match in JS.
# We mirror the JS runtime behavior: only these entries are live matches.
ACRONYMS = {"LLM", "GPT", "API", "JSON", "XML", "YML", "HTML", "URL", "ID"}


def _title_case(s: str) -> str:
    """Title-case a string while preserving known acronyms in upper case.

    Args:
        s: Input string.

    Returns:
        Title-cased string with acronyms preserved.
    """
    def _word(w: str) -> str:
        return w.upper() if w.upper() in ACRONYMS else w.capitalize()

    return re.sub(r"\b\w+", lambda m: _word(m.group()), s)


def _singularize(s: str) -> str:
    """Simple English singularization for deduplication keys.

    Args:
        s: Input string.

    Returns:
        String with simple plural suffix removed.
    """
    s = re.sub(r"ies$", "y", s, flags=re.IGNORECASE)
    s = re.sub(r"(?<!s)s$", "", s, flags=re.IGNORECASE)
    return s


def _dedupe_key(name: str) -> str:
    """Build a deduplication key: lower-cased + singularized."""
    return _singularize(name.strip().lower())


# ── Extraction prompt ─────────────────────────────────────────────────────────

_EXTRACTION_INSTRUCTIONS = """You are an entity and relationship extractor. Given a text chunk, extract structured knowledge.

## OUTPUT FORMAT
Return ONLY valid JSON matching this schema — no markdown fences, no explanation:

{
  "entities": [
    { "name": "Exact Name", "type": "concept|person|technology|organization|technique|other", "description": "One-sentence description" }
  ],
  "relationships": [
    { "source": "Entity A name", "target": "Entity B name", "type": "relates_to|uses|part_of|created_by|influences|contrasts_with|example_of|depends_on", "description": "Brief description of the relationship" }
  ]
}

## RULES
- Extract concrete, meaningful entities — not vague terms like "the model" or "the example"
- Normalize entity names: use canonical/full form (e.g. "GPT-4" not "gpt4", "Chain of Thought" not "CoT")
- Use SINGULAR form for entity names (e.g. "Token" not "Tokens", "Large Language Model" not "Large Language Models")
- Each relationship MUST reference entities that appear in the entities array
- Source and target in a relationship MUST be DIFFERENT entities — no self-references
- ONLY use relationship types from the allowed list above — do not invent new ones
- Prefer specific relationship types over generic "relates_to"
- If the chunk has no meaningful entities, return {"entities":[],"relationships":[]}
- Keep descriptions concise — max 20 words each
- Extract 3-15 entities per chunk (skip trivial ones)
- Every relationship needs both source and target in the entities list"""

EXTRACTION_MODEL = "gpt-5-mini"


# ── Per-chunk post-processing ─────────────────────────────────────────────────

def _normalize_extraction(entities: list[dict], relationships: list[dict]) -> dict:
    """Normalize a single chunk's extraction output.

    Steps:
    - Title-case entity names
    - Clamp entity/relationship types to allowed sets
    - Remove self-referential edges
    - Remap relationship source/target to normalized entity names

    Args:
        entities: Raw entity list from LLM.
        relationships: Raw relationship list from LLM.

    Returns:
        Dict with ``entities`` and ``relationships`` lists.
    """
    name_map: dict[str, str] = {}  # original → normalized
    normalized_entities = []

    for e in entities:
        if not e.get("name") or not e.get("type") or len(e["name"]) <= 1:
            continue
        normalized = _title_case(e["name"].strip())
        name_map[e["name"]] = normalized
        normalized_entities.append({
            "name": normalized,
            "type": e["type"] if e["type"] in ENTITY_TYPES else "other",
            "description": e.get("description", ""),
        })

    entity_names = {e["name"] for e in normalized_entities}

    normalized_rels = []
    for r in relationships:
        src = name_map.get(r.get("source", "")) or _title_case((r.get("source") or "").strip())
        tgt = name_map.get(r.get("target", "")) or _title_case((r.get("target") or "").strip())
        if (
            src != tgt
            and src in entity_names
            and tgt in entity_names
        ):
            normalized_rels.append({
                "source": src,
                "target": tgt,
                "type": r["type"] if r.get("type") in RELATIONSHIP_TYPES else "relates_to",
                "description": r.get("description", ""),
            })

    return {"entities": normalized_entities, "relationships": normalized_rels}


# ── Single chunk extraction ───────────────────────────────────────────────────

async def extract_from_chunk(text: str, context: dict | None = None) -> dict:
    """Extract entities and relationships from a single text chunk.

    Args:
        text: Chunk content.
        context: Optional ``{source, section}`` dict for context hints.

    Returns:
        Dict with ``entities`` and ``relationships`` lists.
    """
    context = context or {}
    hints = [
        f"Source file: {context['source']}" if context.get("source") else None,
        f"Section: {context['section']}" if context.get("section") else None,
    ]
    context_hint = "\n".join(h for h in hints if h)
    prompt = f"{context_hint}\n\n---\n\n{text}" if context_hint else text

    try:
        response = await chat(
            model=EXTRACTION_MODEL,
            input=[{"role": "user", "content": prompt}],
            instructions=_EXTRACTION_INSTRUCTIONS,
            tools=[],
            reasoning=None,
            max_output_tokens=4096,
        )
        raw = extract_text(response)
        if not raw:
            return {"entities": [], "relationships": []}

        # Strip optional markdown fences
        cleaned = re.sub(r"^```json?\n?", "", raw, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
        parsed = json.loads(cleaned)

        return _normalize_extraction(
            parsed.get("entities", []),
            parsed.get("relationships", []),
        )
    except Exception as err:
        log.warn(f"Extraction failed: {err}")
        return {"entities": [], "relationships": []}


# ── Global deduplication ──────────────────────────────────────────────────────

def _deduplicate_global(
    all_entities: list[dict],
    all_relationships: list[dict],
    chunk_entities: dict[int, list[str]],
) -> dict:
    """Deduplicate entities globally across all chunks.

    Merges by lowercased+singularized key, keeps longest description,
    and keeps the longer name form (e.g. prefers "Large Language Model"
    over "LLM"). Remaps all relationship endpoints and chunk entity lists
    to canonical names.

    Args:
        all_entities: All entities from all chunks (may have duplicates).
        all_relationships: All relationships from all chunks.
        chunk_entities: Mapping of chunk index → list of entity names.

    Returns:
        Dict with ``entities``, ``relationships``, and ``chunk_entities``.
    """
    canon_map: dict[str, dict] = {}

    for e in all_entities:
        key = _dedupe_key(e["name"])
        existing = canon_map.get(key)
        if not existing:
            canon_map[key] = dict(e)
        else:
            # Keep longer description
            if len(e.get("description", "")) > len(existing.get("description", "")):
                existing["description"] = e["description"]
            # Keep longer name form
            if len(e["name"]) > len(existing["name"]):
                existing["name"] = e["name"]

    # Build rename map: original name → canonical name
    rename_map: dict[str, str] = {}
    for e in all_entities:
        key = _dedupe_key(e["name"])
        rename_map[e["name"]] = canon_map[key]["name"]

    entities = list(canon_map.values())
    entity_names = {e["name"] for e in entities}

    # Remap relationships and deduplicate identical edges
    seen_edges: set[str] = set()
    relationships: list[dict] = []
    for r in all_relationships:
        src = rename_map.get(r["source"], r["source"])
        tgt = rename_map.get(r["target"], r["target"])
        if src == tgt:
            continue
        if src not in entity_names or tgt not in entity_names:
            continue
        edge_key = f"{src}→{r['type']}→{tgt}"
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        relationships.append({**r, "source": src, "target": tgt})

    # Remap chunk entity lists
    remapped_chunk_entities: dict[int, list[str]] = {}
    for idx, names in chunk_entities.items():
        canonical = list(dict.fromkeys(
            rename_map.get(n, n) for n in names
            if rename_map.get(n, n) in entity_names
        ))
        remapped_chunk_entities[idx] = canonical

    return {
        "entities": entities,
        "relationships": relationships,
        "chunk_entities": remapped_chunk_entities,
    }


# ── Batch extraction ──────────────────────────────────────────────────────────

async def extract_from_chunks(chunks: list[dict]) -> dict:
    """Extract entities and relationships from multiple chunks sequentially.

    Runs extractions sequentially to respect API rate limits, then performs
    a global deduplication pass across all chunks.

    Args:
        chunks: List of ``{content, metadata}`` dicts from the chunker.

    Returns:
        Dict with ``entities``, ``relationships``, and ``chunk_entities``
        (mapping chunk index → list of canonical entity names).
    """
    all_entities: list[dict] = []
    all_relationships: list[dict] = []
    chunk_entities: dict[int, list[str]] = {}

    for i, chunk in enumerate(chunks):
        # Overwrite same line to show progress without flooding terminal
        sys.stdout.write(f"  extracting: {i + 1}/{len(chunks)}\r")
        sys.stdout.flush()

        result = await extract_from_chunk(
            chunk["content"],
            context={
                "section": chunk["metadata"].get("section"),
                "source": chunk["metadata"].get("source"),
            },
        )
        chunk_entities[i] = [e["name"] for e in result["entities"]]
        all_entities.extend(result["entities"])
        all_relationships.extend(result["relationships"])

    if len(chunks) > 1:
        print()  # newline after progress indicator

    deduped = _deduplicate_global(all_entities, all_relationships, chunk_entities)

    log.info(
        f"Extracted {len(all_entities)} raw → {len(deduped['entities'])} unique entities, "
        f"{len(all_relationships)} raw → {len(deduped['relationships'])} unique relationships"
    )

    return deduped
