# -*- coding: utf-8 -*-

#   search.py

"""
### Description:
Hybrid search over Neo4j: full-text (BM25) + vector (cosine) with
Reciprocal Rank Fusion (RRF). Also provides graph traversal helpers
(getNeighbors, findPaths, safeReadCypher) used by agent tools.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/graph/search.js`

"""

from neo4j import AsyncDriver

from .driver import read_query
from .embeddings import embed
from ..helpers.logger import log

RRF_K = 60


# ── Full-text search ──────────────────────────────────────────────────────────

async def search_full_text(driver: AsyncDriver, query: str, limit: int = 10) -> list[dict]:
    """Search chunks using Neo4j full-text index (Lucene / BM25).

    Args:
        driver: Neo4j async driver.
        query: Keyword query string.
        limit: Maximum results to return.

    Returns:
        List of chunk dicts with ``content``, ``section``, ``chunkIndex``,
        ``source``, and ``ftsScore`` fields.
    """
    if not query.strip():
        return []
    try:
        records = await read_query(
            driver,
            """CALL db.index.fulltext.queryNodes("chunk_content_ft", $query, {limit: $limit})
               YIELD node, score
               RETURN node.content AS content,
                      node.section AS section,
                      node.chunkIndex AS chunkIndex,
                      node.source AS source,
                      score""",
            {"query": query, "limit": limit},
        )
        return [
            {
                "content": r["content"],
                "section": r["section"],
                # neo4j integers may be Integer objects; convert to plain int
                "chunkIndex": int(r["chunkIndex"]) if r["chunkIndex"] is not None else 0,
                "source": r["source"],
                "ftsScore": r["score"],
            }
            for r in records
        ]
    except Exception:
        return []


# ── Vector search ─────────────────────────────────────────────────────────────

async def search_vector(
    driver: AsyncDriver, query_embedding: list[float], limit: int = 10
) -> list[dict]:
    """Search chunks using Neo4j vector index (cosine similarity).

    Args:
        driver: Neo4j async driver.
        query_embedding: Query vector (1536 dimensions).
        limit: Maximum results to return.

    Returns:
        List of chunk dicts with ``vecScore`` field (higher = more similar).
    """
    records = await read_query(
        driver,
        """CALL db.index.vector.queryNodes("chunk_embedding_vec", $limit, $embedding)
           YIELD node, score
           RETURN node.content AS content,
                  node.section AS section,
                  node.chunkIndex AS chunkIndex,
                  node.source AS source,
                  score""",
        {"embedding": query_embedding, "limit": limit},
    )
    return [
        {
            "content": r["content"],
            "section": r["section"],
            "chunkIndex": int(r["chunkIndex"]) if r["chunkIndex"] is not None else 0,
            "source": r["source"],
            "vecScore": r["score"],
        }
        for r in records
    ]


# ── Hybrid search with RRF fusion ─────────────────────────────────────────────

async def hybrid_search(
    driver: AsyncDriver,
    *,
    keywords: str,
    semantic: str,
    limit: int = 5,
) -> list[dict]:
    """Hybrid retrieval: full-text BM25 + semantic vector, fused via RRF.

    Runs FTS and vector search in parallel where possible, then merges
    results using Reciprocal Rank Fusion (k=60) and returns the top ``limit``
    chunks.

    Args:
        driver: Neo4j async driver.
        keywords: Keyword string for full-text matching.
        semantic: Natural-language query for semantic embedding.
        limit: Number of fused results to return.

    Returns:
        List of chunk dicts (rrf/internal rank fields stripped).
    """
    fts_limit = limit * 3

    log.search_header(keywords, semantic)

    # FTS first (always available)
    fts_results = await search_full_text(driver, keywords, fts_limit)
    log.search_fts([{**r, "fts_score": r["ftsScore"], "chunk_index": r["chunkIndex"]} for r in fts_results])

    # Vector search — degrade gracefully on embedding failure
    vec_results: list[dict] = []
    try:
        query_embedding = (await embed(semantic))[0]
        vec_results = await search_vector(driver, query_embedding, fts_limit)
    except Exception as err:
        log.warn(f"Semantic search unavailable: {err}")
    log.search_vec([{**r, "vec_distance": 1.0 - (r.get("vecScore") or 0.0), "chunk_index": r["chunkIndex"]} for r in vec_results])

    # Build RRF score map keyed by source::chunkIndex
    scores: dict[str, dict] = {}

    def _key(r: dict) -> str:
        return f"{r['source']}::{r['chunkIndex']}"

    def _upsert(key: str, data: dict) -> dict:
        if key not in scores:
            scores[key] = {**data, "rrf": 0.0}
        return scores[key]

    for rank, r in enumerate(fts_results):
        entry = _upsert(_key(r), r)
        entry["rrf"] += 1.0 / (RRF_K + rank + 1)
        entry["fts_rank"] = rank + 1

    for rank, r in enumerate(vec_results):
        entry = _upsert(_key(r), r)
        entry["rrf"] += 1.0 / (RRF_K + rank + 1)
        entry["vec_rank"] = rank + 1

    merged = sorted(scores.values(), key=lambda x: x["rrf"], reverse=True)[:limit]

    log.search_rrf([{**r, "chunk_index": r["chunkIndex"]} for r in merged])

    # Strip internal rank fields before returning
    return [
        {k: v for k, v in r.items() if k not in ("rrf", "ftsScore", "vecScore", "fts_rank", "vec_rank")}
        for r in merged
    ]


# ── Entity enrichment ─────────────────────────────────────────────────────────

async def get_entities_for_chunks(
    driver: AsyncDriver, chunks: list[dict]
) -> dict:
    """Return entities mentioned in the given chunks.

    Args:
        driver: Neo4j async driver.
        chunks: List of chunk dicts with ``source`` and ``chunkIndex`` fields.

    Returns:
        Dict with:
        - ``chunkEntities``: mapping of ``"source::chunkIndex"`` → list of
          ``{name, type}`` entity dicts.
        - ``allEntities``: de-duplicated flat list of all entity dicts.
    """
    if not chunks:
        return {"chunkEntities": {}, "allEntities": []}

    records = await read_query(
        driver,
        """UNWIND $chunks AS c
           MATCH (ch:Chunk {source: c.source, chunkIndex: c.chunkIndex})-[:MENTIONS]->(e:Entity)
           RETURN c.source AS source, c.chunkIndex AS chunkIndex,
                  collect(DISTINCT {name: e.name, type: e.type}) AS entities""",
        {"chunks": [{"source": c["source"], "chunkIndex": c["chunkIndex"]} for c in chunks]},
    )

    chunk_entities: dict[str, list] = {}
    all_entity_map: dict[str, dict] = {}

    for r in records:
        idx = int(r["chunkIndex"]) if r["chunkIndex"] is not None else 0
        key = f"{r['source']}::{idx}"
        entities = r["entities"]
        chunk_entities[key] = entities
        for e in entities:
            all_entity_map[e["name"]] = e

    return {"chunkEntities": chunk_entities, "allEntities": list(all_entity_map.values())}


# ── Graph traversal helpers ───────────────────────────────────────────────────

async def get_neighbors(
    driver: AsyncDriver, entity_name: str, limit: int = 20
) -> dict | None:
    """Return an entity and all its directly connected neighbors.

    Args:
        driver: Neo4j async driver.
        entity_name: Entity name (case-insensitive).
        limit: Maximum neighbors to return.

    Returns:
        Dict with ``name``, ``type``, ``description``, ``neighbors``,
        or ``None`` if the entity is not found.
    """
    records = await read_query(
        driver,
        """MATCH (e:Entity)
           WHERE toLower(e.name) = toLower($name)
           OPTIONAL MATCH (e)-[r:RELATED_TO]-(other:Entity)
           RETURN e.name AS name, e.type AS type, e.description AS description,
                  collect(DISTINCT {
                    entity: other.name,
                    entityType: other.type,
                    relType: r.type,
                    relDescription: r.description,
                    evidenceSource: r.evidenceSource,
                    direction: CASE WHEN startNode(r) = e THEN 'outgoing' ELSE 'incoming' END
                  })[0..$limit] AS neighbors""",
        {"name": entity_name, "limit": limit},
    )

    if not records:
        return None

    r = records[0]
    neighbors = [n for n in (r["neighbors"] or []) if n.get("entity") is not None]
    return {
        "name": r["name"],
        "type": r["type"],
        "description": r["description"],
        "neighbors": neighbors,
    }


async def find_paths(
    driver: AsyncDriver,
    from_entity: str,
    to_entity: str,
    max_depth: int = 4,
) -> list[dict]:
    """Find shortest path(s) between two entities via RELATED_TO edges.

    Args:
        driver: Neo4j async driver.
        from_entity: Starting entity name (case-insensitive).
        to_entity: Target entity name (case-insensitive).
        max_depth: Maximum relationship hops (default 4, max 6).

    Returns:
        List of path dicts with ``nodes`` and ``edges`` arrays (up to 3 paths).
    """
    records = await read_query(
        driver,
        f"""MATCH (a:Entity), (b:Entity)
            WHERE toLower(a.name) = toLower($from) AND toLower(b.name) = toLower($to)
            MATCH path = shortestPath((a)-[:RELATED_TO*1..{max_depth}]-(b))
            RETURN [n IN nodes(path) | {{name: n.name, type: n.type}}] AS nodes,
                   [r IN relationships(path) | {{type: r.type, description: r.description, evidenceSource: r.evidenceSource}}] AS edges
            LIMIT 3""",
        {"from": from_entity, "to": to_entity},
    )
    return [{"nodes": r["nodes"], "edges": r["edges"]} for r in records]


async def safe_read_cypher(
    driver: AsyncDriver,
    cypher: str,
    params: dict | None = None,
    limit: int = 25,
) -> list[dict]:
    """Execute a read-only Cypher query with basic write-guard protection.

    Rejects queries containing write keywords (CREATE, MERGE, DELETE, etc.)
    and automatically appends a LIMIT clause if none is present.

    Args:
        driver: Neo4j async driver.
        cypher: Cypher query string.
        params: Query parameters.
        limit: Auto-appended limit when the query has none.

    Returns:
        List of result row dicts.

    Raises:
        ValueError: If write keywords are detected.
    """
    params = params or {}
    upper = cypher.upper()
    write_keywords = ["CREATE", "MERGE", "DELETE", "SET ", "REMOVE", "DROP", "CALL {"]
    if any(kw in upper for kw in write_keywords):
        raise ValueError("Write operations are not allowed in read-only Cypher tool")

    safe_cypher = cypher if "LIMIT" in upper else f"{cypher}\nLIMIT {limit}"
    records = await read_query(driver, safe_cypher, params)

    def _coerce(v):
        try:
            return int(v)
        except (TypeError, ValueError, AttributeError):
            return v

    return [
        {key: _coerce(r[key]) if hasattr(r[key], "value") else r[key] for key in r.keys()}
        for r in records
    ]
