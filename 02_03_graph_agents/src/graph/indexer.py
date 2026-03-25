# -*- coding: utf-8 -*-

#   indexer.py

"""
### Description:
Workspace indexer for the Neo4j knowledge graph. Orchestrates the full
ingestion pipeline per file: hash check → chunk → embed → extract entities
→ embed entities → write to Neo4j in a single transaction.
Also provides graph curation helpers: removeDocument, clearGraph, auditGraph,
mergeEntities.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/graph/indexer.js`

"""

import hashlib
import sys
from pathlib import Path

from neo4j import AsyncDriver

from .chunking import chunk_by_separators
from .driver import read_query, write_query, write_transaction
from .embeddings import embed
from .extract import extract_from_chunks
from ..helpers.logger import log

BATCH_SIZE = 20
SUPPORTED_EXTENSIONS = {".md", ".txt"}


# ── Utilities ─────────────────────────────────────────────────────────────────

def _hash_content(content: str) -> str:
    """Return a SHA-256 hex digest of the given string."""
    return hashlib.sha256(content.encode()).hexdigest()


async def _batch_embed(texts: list[str], label: str) -> list[list[float]]:
    """Embed texts in batches of ``BATCH_SIZE``, showing progress.

    Args:
        texts: List of strings to embed.
        label: Display label for progress output (e.g. ``"chunk"``).

    Returns:
        List of float vectors in input order.
    """
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]
        embeddings.extend(await embed(batch))
        sys.stdout.write(f"  {label} embeddings: {len(embeddings)}/{len(texts)}\r")
        sys.stdout.flush()
    if len(texts) > BATCH_SIZE:
        print()
    return embeddings


def _deduplicate_entities(entities: list[dict]) -> list[dict]:
    """Deduplicate by ``(name, type)`` — keep the longest description.

    Args:
        entities: Entity list (may contain duplicates).

    Returns:
        De-duplicated entity list.
    """
    seen: dict[str, dict] = {}
    for e in entities:
        key = f"{e['name']}::{e['type']}"
        existing = seen.get(key)
        if not existing or len(e.get("description", "")) > len(existing.get("description", "")):
            seen[key] = e
    return list(seen.values())


# ── Document removal ──────────────────────────────────────────────────────────

async def remove_document(driver: AsyncDriver, source: str) -> None:
    """Remove a document and all its chunks from the graph.

    Entities that are no longer mentioned by any chunk after removal are also
    deleted (orphan pruning).

    Args:
        driver: Neo4j async driver.
        source: Document source identifier.
    """
    await write_query(
        driver,
        """MATCH (d:Document {source: $source})
           OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
           OPTIONAL MATCH (c)-[:MENTIONS]->(e:Entity)
           DETACH DELETE c, d
           WITH e WHERE e IS NOT NULL
           AND NOT EXISTS { (e)<-[:MENTIONS]-(:Chunk) }
           DETACH DELETE e""",
        {"source": source},
    )


# ── Core indexing pipeline ────────────────────────────────────────────────────

async def _index_content(driver: AsyncDriver, content: str, source: str) -> dict:
    """Index raw text content into the Neo4j graph.

    Runs the full pipeline: chunk → embed chunks → extract entities →
    embed entities → write document/chunk/entity nodes and relationships
    in a single transaction.

    Skips unchanged documents (same SHA-256 hash), and re-indexes changed ones.

    Args:
        driver: Neo4j async driver.
        content: Document text to index.
        source: Unique source identifier (filename or custom label).

    Returns:
        Stats dict with ``chunks``, ``entities``, ``relationships`` counts,
        plus ``skipped: True`` when unchanged.
    """
    if not content.strip():
        log.warn(f"Skipping empty content: {source}")
        return {"chunks": 0, "entities": 0, "relationships": 0}

    content_hash = _hash_content(content)

    # Check if already indexed with the same hash
    existing = await read_query(
        driver,
        "MATCH (d:Document {source: $source}) RETURN d.hash AS hash",
        {"source": source},
    )

    if existing and existing[0]["hash"] == content_hash:
        log.info(f"Skipping {source} (unchanged)")
        return {"chunks": 0, "entities": 0, "relationships": 0, "skipped": True}

    if existing:
        log.info(f"Re-indexing {source} (changed)")
        await remove_document(driver, source)

    # 1. Chunk
    chunks = chunk_by_separators(content, source=source)
    log.info(f"{source}: {len(chunks)} chunks")

    # 2. Embed chunks
    chunk_texts = [c["content"] for c in chunks]
    chunk_embeddings = await _batch_embed(chunk_texts, "chunk")

    # 3. Extract entities & relationships
    log.start("Extracting entities...")
    extracted = await extract_from_chunks(chunks)
    entities = extracted["entities"]
    relationships = extracted["relationships"]
    chunk_entities = extracted["chunk_entities"]

    # 4. Embed unique entities
    unique_entities = _deduplicate_entities(entities)
    entity_embeddings: list[list[float]] = []
    if unique_entities:
        entity_texts = [f"{e['name']}: {e.get('description') or e['type']}" for e in unique_entities]
        entity_embeddings = await _batch_embed(entity_texts, "entity")

    # 5. Write everything to Neo4j in one transaction
    async def _write(tx):  # type: ignore[no-untyped-def]
        # Document node
        await tx.run(
            "CREATE (d:Document {source: $source, hash: $hash, indexedAt: datetime()})",
            {"source": source, "hash": content_hash},
        )

        # Chunk nodes + HAS_CHUNK edges
        for i, chunk in enumerate(chunks):
            await tx.run(
                """MATCH (d:Document {source: $source})
                   CREATE (d)-[:HAS_CHUNK]->(c:Chunk {
                     content: $content,
                     chunkIndex: $index,
                     section: $section,
                     chars: $chars,
                     source: $source,
                     embedding: $embedding
                   })""",
                {
                    "source": source,
                    "content": chunk["content"],
                    "index": chunk["metadata"]["index"],
                    "section": chunk["metadata"].get("section") or "",
                    "chars": chunk["metadata"]["chars"],
                    "embedding": chunk_embeddings[i],
                },
            )

        # Entity nodes — MERGE to deduplicate across sources
        for i, entity in enumerate(unique_entities):
            await tx.run(
                """MERGE (e:Entity {name: $name, type: $type})
                   ON CREATE SET e.description = $description,
                                 e.aliases_text = $name,
                                 e.embedding = $embedding
                   ON MATCH SET  e.description = CASE
                     WHEN size(e.description) < size($description)
                     THEN $description ELSE e.description END""",
                {
                    "name": entity["name"],
                    "type": entity["type"],
                    "description": entity.get("description", ""),
                    "embedding": entity_embeddings[i] if i < len(entity_embeddings) else [],
                },
            )

        # MENTIONS edges: Chunk → Entity
        for chunk_idx, entity_names in chunk_entities.items():
            for ename in entity_names:
                await tx.run(
                    """MATCH (c:Chunk {source: $source, chunkIndex: $chunkIdx})
                       MATCH (e:Entity {name: $eName})
                       MERGE (c)-[:MENTIONS]->(e)""",
                    {"source": source, "chunkIdx": chunk_idx, "eName": ename},
                )

        # RELATED_TO edges between entities
        for rel in relationships:
            await tx.run(
                """MATCH (a:Entity {name: $source})
                   MATCH (b:Entity {name: $target})
                   MERGE (a)-[r:RELATED_TO {type: $type}]->(b)
                   ON CREATE SET r.description = $description,
                                 r.evidenceSource = $evidenceSource""",
                {
                    "source": rel["source"],
                    "target": rel["target"],
                    "type": rel["type"],
                    "description": rel.get("description", ""),
                    "evidenceSource": source,
                },
            )

    await write_transaction(driver, _write)

    stats = {
        "chunks": len(chunks),
        "entities": len(unique_entities),
        "relationships": len(relationships),
    }
    log.success(
        f"Indexed {source}: {stats['chunks']} chunks, "
        f"{stats['entities']} entities, {stats['relationships']} relationships"
    )
    return stats


async def index_file(driver: AsyncDriver, file_path: Path, file_name: str) -> dict:
    """Index a file from disk into the graph.

    Args:
        driver: Neo4j async driver.
        file_path: Absolute path to the file.
        file_name: Name used as the source identifier in the graph.

    Returns:
        Stats dict (see ``_index_content``).
    """
    content = file_path.read_text(encoding="utf-8")
    return await _index_content(driver, content, file_name)


async def index_text(driver: AsyncDriver, text: str, source: str) -> dict:
    """Index raw text into the graph without a backing file.

    Args:
        driver: Neo4j async driver.
        text: Raw text content to index.
        source: Unique source label (e.g. ``"note:meeting-2024-02-11"``).

    Returns:
        Stats dict (see ``_index_content``).
    """
    return await _index_content(driver, text, source)


# ── Workspace indexing ────────────────────────────────────────────────────────

async def index_workspace(driver: AsyncDriver, workspace_path: str | Path) -> None:
    """Index all supported files in the workspace directory.

    Creates the directory if it doesn't exist. After indexing, prunes any
    ``Document`` nodes whose source files are no longer on disk.

    Args:
        driver: Neo4j async driver.
        workspace_path: Path to the workspace directory (relative or absolute).
    """
    workspace = Path(workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)

    files = [
        f for f in workspace.iterdir()
        if f.is_file() and f.suffix in SUPPORTED_EXTENSIONS
    ]

    if not files:
        log.warn(f"No .md/.txt files found in {workspace}")
        return

    log.info(f"Found {len(files)} file(s) in {workspace}")

    for f in files:
        await index_file(driver, f, f.name)

    # Prune documents that no longer exist on disk
    indexed = await read_query(driver, "MATCH (d:Document) RETURN d.source AS source")
    on_disk = {f.name for f in files}

    for record in indexed:
        source = record["source"]
        if source not in on_disk:
            log.info(f"Removing stale index: {source}")
            await remove_document(driver, source)


# ── Graph curation helpers ────────────────────────────────────────────────────

async def clear_graph(driver: AsyncDriver) -> None:
    """Wipe all nodes and relationships from the graph.

    Args:
        driver: Neo4j async driver.
    """
    records = await write_query(
        driver,
        "MATCH (n) DETACH DELETE n RETURN count(n) AS deleted",
    )
    deleted = records[0]["deleted"] if records else 0
    # neo4j integers may be wrapped objects; call int() for safety
    try:
        deleted = int(deleted)
    except (TypeError, ValueError):
        deleted = 0
    log.info(f"Cleared {deleted} nodes")


async def audit_graph(driver: AsyncDriver) -> dict:
    """Return a health report for the knowledge graph.

    Returns:
        Dict with ``nodeCounts``, ``orphanEntities``, ``potentialDuplicates``,
        ``relationshipTypes``, and ``entityTypes``.
    """
    import asyncio

    async def _counts():
        return await read_query(
            driver,
            "MATCH (n) WITH labels(n)[0] AS label, count(n) AS count "
            "RETURN label, count ORDER BY count DESC",
        )

    async def _orphans():
        return await read_query(
            driver,
            "MATCH (e:Entity) WHERE NOT (e)-[:RELATED_TO]-() "
            "RETURN e.name AS name, e.type AS type",
        )

    async def _duplicates():
        return await read_query(
            driver,
            """MATCH (a:Entity), (b:Entity)
               WHERE id(a) < id(b) AND a.type = b.type
                 AND (a.name CONTAINS b.name OR b.name CONTAINS a.name)
                 AND a.name <> b.name
               RETURN a.name AS a, b.name AS b, a.type AS type
               LIMIT 20""",
        )

    async def _rel_types():
        return await read_query(
            driver,
            "MATCH ()-[r:RELATED_TO]->() "
            "RETURN r.type AS type, count(r) AS count ORDER BY count DESC",
        )

    async def _entity_types():
        return await read_query(
            driver,
            "MATCH (e:Entity) "
            "RETURN e.type AS type, count(e) AS count ORDER BY count DESC",
        )

    counts, orphans, duplicates, rel_types, ent_types = await asyncio.gather(
        _counts(), _orphans(), _duplicates(), _rel_types(), _entity_types()
    )

    def _int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return v

    return {
        "nodeCounts": [{"label": r["label"], "count": _int(r["count"])} for r in counts],
        "orphanEntities": [{"name": r["name"], "type": r["type"]} for r in orphans],
        "potentialDuplicates": [{"a": r["a"], "b": r["b"], "type": r["type"]} for r in duplicates],
        "relationshipTypes": [{"type": r["type"], "count": _int(r["count"])} for r in rel_types],
        "entityTypes": [{"type": r["type"], "count": _int(r["count"])} for r in ent_types],
    }


async def merge_entities(
    driver: AsyncDriver, source_name: str, target_name: str
) -> dict | None:
    """Merge a duplicate entity into a canonical one.

    Rewires all MENTIONS and RELATED_TO edges from ``source_name`` to
    ``target_name``, then deletes the source entity node.

    Args:
        driver: Neo4j async driver.
        source_name: Entity to merge away (will be deleted).
        target_name: Canonical entity to keep.

    Returns:
        ``{merged, into}`` dict, or ``None`` if either entity was not found.
    """
    result: dict | None = None

    async def _merge(tx):  # type: ignore[no-untyped-def]
        nonlocal result

        # Verify both exist — must consume AsyncResult inside the transaction
        check = await tx.run(
            """MATCH (s:Entity) WHERE toLower(s.name) = toLower($source)
               MATCH (t:Entity) WHERE toLower(t.name) = toLower($target)
               RETURN s.name AS sName, t.name AS tName""",
            {"source": source_name, "target": target_name},
        )
        records = await check.data()
        if not records:
            return

        # Rewire MENTIONS edges
        await tx.run(
            """MATCH (c:Chunk)-[old:MENTIONS]->(s:Entity)
               WHERE toLower(s.name) = toLower($source)
               MATCH (t:Entity) WHERE toLower(t.name) = toLower($target)
               MERGE (c)-[:MENTIONS]->(t)
               DELETE old""",
            {"source": source_name, "target": target_name},
        )

        # Rewire outgoing RELATED_TO
        await tx.run(
            """MATCH (s:Entity)-[old:RELATED_TO]->(other:Entity)
               WHERE toLower(s.name) = toLower($source)
               MATCH (t:Entity) WHERE toLower(t.name) = toLower($target)
               MERGE (t)-[r:RELATED_TO {type: old.type}]->(other)
               ON CREATE SET r.description = old.description,
                             r.evidenceSource = old.evidenceSource
               DELETE old""",
            {"source": source_name, "target": target_name},
        )

        # Rewire incoming RELATED_TO
        await tx.run(
            """MATCH (other:Entity)-[old:RELATED_TO]->(s:Entity)
               WHERE toLower(s.name) = toLower($source)
               MATCH (t:Entity) WHERE toLower(t.name) = toLower($target)
               MERGE (other)-[r:RELATED_TO {type: old.type}]->(t)
               ON CREATE SET r.description = old.description,
                             r.evidenceSource = old.evidenceSource
               DELETE old""",
            {"source": source_name, "target": target_name},
        )

        # Delete source entity
        await tx.run(
            "MATCH (s:Entity) WHERE toLower(s.name) = toLower($source) DETACH DELETE s",
            {"source": source_name},
        )

        result = {"merged": records[0]["sName"], "into": records[0]["tName"]}  # type: ignore[index]

    await write_transaction(driver, _merge)
    return result
