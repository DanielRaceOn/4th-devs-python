# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Agent tool definitions and handlers for graph-based RAG.

Retrieval tools:  search, explore, connect, cypher
Curation tools:   learn, forget, merge_entities, audit

Each handler wraps the underlying graph functions and returns JSON-serialized
results to the LLM. Errors are caught and returned as {error: ...} dicts.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/agent/tools.js`

"""

import json
from pathlib import Path

from neo4j import AsyncDriver

from ..graph.search import (
    hybrid_search,
    get_entities_for_chunks,
    get_neighbors,
    find_paths,
    safe_read_cypher,
)
from ..graph.indexer import (
    index_file,
    index_text,
    remove_document,
    audit_graph,
    merge_entities,
)
from ..helpers.logger import log

# Anchored to the module root so it resolves correctly regardless of CWD
WORKSPACE_DIR = Path(__file__).parent.parent.parent / "workspace"

# ── Tool definitions sent to the LLM ─────────────────────────────────────────

TOOLS = [
    # ── Retrieval ─────────────────────────────────────────────────────────────
    {
        "type": "function",
        "name": "search",
        "description": (
            "Search the knowledge base using hybrid retrieval (full-text BM25 + semantic vector). "
            "Returns matching document chunks AND the graph entities mentioned in those chunks. "
            "Use this as your first tool for any question — it gives you both text evidence and entity handles "
            "you can pass to 'explore' or 'connect' for deeper graph traversal."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": (
                        "Keywords for full-text matching — names, terms, and phrases that should appear "
                        "literally in the text. Example: 'GPT-4 autoregression token prediction'"
                    ),
                },
                "semantic": {
                    "type": "string",
                    "description": (
                        "Natural language query for semantic matching — describe the concept or question "
                        "in plain English. Example: 'How do language models generate text one token at a time?'"
                    ),
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum chunks to return (default: 5, max: 20)",
                },
            },
            "required": ["keywords", "semantic"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "explore",
        "description": (
            "Explore the knowledge graph around a specific entity. Returns the entity's metadata and all "
            "directly connected entities with relationship types, descriptions, and evidence sources. "
            "Use AFTER search to follow connections: pass an entity name from search results to see what it relates to. "
            "The entity name is case-insensitive."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entity": {
                    "type": "string",
                    "description": (
                        "Entity name to explore — use a name from search results' 'entities' array. "
                        "Example: 'Prompt Engineering'"
                    ),
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum neighbors to return (default: 20, max: 50)",
                },
            },
            "required": ["entity"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "connect",
        "description": (
            "Find how two entities are connected through the knowledge graph. Returns the shortest path(s): "
            "the chain of entities and relationships linking them, with evidence sources for each edge. "
            "Use when the user asks how two concepts relate, or to discover indirect connections. "
            "Entity names are case-insensitive."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "from": {
                    "type": "string",
                    "description": "Starting entity name. Example: 'GPT-4'",
                },
                "to": {
                    "type": "string",
                    "description": "Target entity name. Example: 'Chain Of Thought'",
                },
                "maxDepth": {
                    "type": "number",
                    "description": (
                        "Maximum relationship hops (default: 4, max: 6). "
                        "Increase only if default yields no path."
                    ),
                },
            },
            "required": ["from", "to"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "cypher",
        "description": (
            "Execute a read-only Cypher query against the knowledge graph. Use ONLY when the other tools "
            "cannot express what you need (e.g. aggregations, filtering by type, counting relationships). "
            "Schema: "
            "(:Document {source, hash})-[:HAS_CHUNK]->(:Chunk {content, section, source, chunkIndex})"
            "-[:MENTIONS]->(:Entity {name, type, description}), "
            "(:Entity)-[:RELATED_TO {type, description, evidenceSource}]->(:Entity). "
            "Entity types: concept, person, technology, organization, technique, other. "
            "Relationship types: relates_to, uses, part_of, created_by, influences, contrasts_with, example_of, depends_on. "
            "ONLY read queries — no CREATE, MERGE, DELETE, SET, DROP."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Cypher query string. Use $paramName for parameters. "
                        "Example: 'MATCH (e:Entity {type: $type}) RETURN e.name, e.description LIMIT 10'"
                    ),
                },
                "params": {
                    "type": "object",
                    "description": "Parameters to substitute into the query. Example: {type: 'technique'}",
                },
            },
            "required": ["query"],
        },
        "strict": False,
    },
    # ── Curation ──────────────────────────────────────────────────────────────
    {
        "type": "function",
        "name": "learn",
        "description": (
            "Index content into the knowledge graph. Runs the full pipeline: "
            "chunk → embed → extract entities & relationships → write to graph. "
            "Two modes: pass 'filename' to index a file from workspace/, or pass 'text' + 'source' to index raw text. "
            "Use when the user asks you to learn, index, memorize, or remember something."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": (
                        "Filename inside workspace/ directory. Use this to index a file. "
                        "Example: 'article.md'"
                    ),
                },
                "text": {
                    "type": "string",
                    "description": (
                        "Raw text content to index directly (no file needed). "
                        "Use this when the user shares information in conversation."
                    ),
                },
                "source": {
                    "type": "string",
                    "description": (
                        "Label for raw text content (required when using 'text', ignored when using 'filename'). "
                        "Example: 'note:meeting-2024-02-11', 'user:api-architecture'"
                    ),
                },
            },
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "forget",
        "description": (
            "Remove content and all its chunks, entity mentions, and orphaned entities from the graph. "
            "Pass the source identifier: a filename (e.g. 'article.md') or a source label used during learn."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": (
                        "Source identifier to remove — a filename or source label. "
                        "Example: 'article.md' or 'note:meeting'"
                    ),
                },
            },
            "required": ["source"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "merge_entities",
        "description": (
            "Merge a duplicate entity into a canonical one. Moves all relationships and chunk mentions "
            "from source entity to target entity, then deletes the source. "
            "Use after 'audit' reveals duplicates. Example: merge 'LLM' into 'Large Language Model'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Entity name to merge away (will be deleted after rewiring edges)",
                },
                "target": {
                    "type": "string",
                    "description": "Canonical entity name to keep (receives all edges from source)",
                },
            },
            "required": ["source", "target"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "audit",
        "description": (
            "Diagnose knowledge graph quality. Returns: node counts by label, orphan entities (no RELATED_TO edges), "
            "potential duplicate entities (name substring matches), relationship type distribution, "
            "and entity type distribution. Use to assess graph health before using merge_entities."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "strict": False,
    },
]


# ── Tool factory ──────────────────────────────────────────────────────────────

def create_tools(driver: AsyncDriver) -> dict:
    """Create tool handler registry bound to the Neo4j driver.

    Args:
        driver: Neo4j async driver.

    Returns:
        Dict with ``definitions`` (list of tool schemas) and ``handle``
        (async callable accepting ``name`` and ``args``).
    """
    handlers = {
        "search": _handle_search,
        "explore": _handle_explore,
        "connect": _handle_connect,
        "cypher": _handle_cypher,
        "learn": _handle_learn,
        "forget": _handle_forget,
        "merge_entities": _handle_merge_entities,
        "audit": _handle_audit,
    }

    async def handle(name: str, args: dict) -> str:
        """Dispatch a tool call by name and return JSON-serialized result.

        Args:
            name: Tool name.
            args: Parsed argument dict.

        Returns:
            JSON string (result or ``{error: "..."}``).
        """
        handler = handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")

        log.tool(name, args)

        try:
            result = await handler(driver, args)
            output = json.dumps(result, ensure_ascii=False)
            log.tool_result(name, True, output)
            return output
        except Exception as err:
            output = json.dumps({"error": str(err)})
            log.tool_result(name, False, str(err))
            return output

    return {"definitions": TOOLS, "handle": handle}


# ── Individual handlers ───────────────────────────────────────────────────────

async def _handle_search(driver: AsyncDriver, args: dict) -> dict:
    keywords = args.get("keywords", "")
    semantic = args.get("semantic", "")
    limit = min(int(args.get("limit", 5)), 20)

    chunks = await hybrid_search(driver, keywords=keywords, semantic=semantic, limit=limit)
    enriched = await get_entities_for_chunks(driver, chunks)
    chunk_entities = enriched["chunkEntities"]
    all_entities = enriched["allEntities"]

    return {
        "chunks": [
            {
                "source": c["source"],
                "section": c.get("section"),
                "content": c["content"],
                "entities": [
                    e["name"]
                    for e in chunk_entities.get(f"{c['source']}::{c['chunkIndex']}", [])
                ],
            }
            for c in chunks
        ],
        "entities": all_entities,
    }


async def _handle_explore(driver: AsyncDriver, args: dict) -> dict:
    entity = args.get("entity", "")
    limit = min(int(args.get("limit", 20)), 50)
    result = await get_neighbors(driver, entity, limit)
    if result is None:
        return {"error": f'Entity "{entity}" not found in graph. Check spelling or use search first.'}
    return result


async def _handle_connect(driver: AsyncDriver, args: dict) -> dict:
    from_ent = args.get("from", "")
    to_ent = args.get("to", "")
    max_depth = min(int(args.get("maxDepth", 4)), 6)
    paths = await find_paths(driver, from_ent, to_ent, max_depth)
    if not paths:
        return {"error": f'No path found between "{from_ent}" and "{to_ent}" within {max_depth} hops.'}
    return {"paths": paths}


async def _handle_cypher(driver: AsyncDriver, args: dict) -> list | dict:
    query = args.get("query", "")
    params = args.get("params") or {}
    return await safe_read_cypher(driver, query, params)


async def _handle_learn(driver: AsyncDriver, args: dict) -> dict:
    filename = args.get("filename")
    text = args.get("text")
    source = args.get("source")

    if filename:
        # Mode 1: index a file from workspace/
        available = [f.name for f in WORKSPACE_DIR.iterdir() if f.is_file()]
        if filename not in available:
            return {"error": f'File "{filename}" not found in workspace/. Available: {", ".join(available)}'}
        stats = await index_file(driver, WORKSPACE_DIR / filename, filename)
        if stats.get("skipped"):
            return {"success": True, "message": f'"{filename}" already indexed (unchanged)'}
        return {
            "success": True,
            "message": (
                f'Indexed "{filename}": {stats["chunks"]} chunks, '
                f'{stats["entities"]} entities, {stats["relationships"]} relationships'
            ),
        }

    if text:
        # Mode 2: index raw text
        if not source or not source.strip():
            return {"error": "Source label is required when indexing raw text"}
        if not text.strip():
            return {"error": "Text content is empty"}
        stats = await index_text(driver, text, source)
        if stats.get("skipped"):
            return {"success": True, "message": f'"{source}" already indexed (unchanged)'}
        return {
            "success": True,
            "message": (
                f'Indexed "{source}": {stats["chunks"]} chunks, '
                f'{stats["entities"]} entities, {stats["relationships"]} relationships'
            ),
        }

    return {"error": "Provide either 'filename' to index a file, or 'text' + 'source' to index raw text"}


async def _handle_forget(driver: AsyncDriver, args: dict) -> dict:
    source = args.get("source", "")
    await remove_document(driver, source)
    return {"success": True, "message": f'Removed "{source}" and its data from the graph'}


async def _handle_merge_entities(driver: AsyncDriver, args: dict) -> dict:
    source = args.get("source", "")
    target = args.get("target", "")
    result = await merge_entities(driver, source, target)
    if result is None:
        return {"error": f'One or both entities not found: "{source}", "{target}"'}
    return {"success": True, "message": f'Merged "{result["merged"]}" into "{result["into"]}"'}


async def _handle_audit(driver: AsyncDriver, args: dict) -> dict:
    return await audit_graph(driver)
