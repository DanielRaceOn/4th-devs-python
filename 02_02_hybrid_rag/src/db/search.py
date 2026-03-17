# -*- coding: utf-8 -*-

#   search.py

"""
### Description:
Hybrid search: FTS5 (BM25) + sqlite-vec (vector similarity) combined with
Reciprocal Rank Fusion (RRF). Each subsystem is run independently with
different query strings; results are merged by chunk ID and ranked.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/db/search.js

"""

import re
import sqlite3
import struct
from typing import Any, Dict, List, Optional

from .embeddings import embed
from ..helpers import logger as log

RRF_K = 60  # standard RRF constant that balances rank contributions


def _to_vec_bytes(arr: List[float]) -> bytes:
    """Pack a float list to IEEE 754 single-precision bytes for sqlite-vec."""
    return struct.pack(f"{len(arr)}f", *arr)


def _to_fts_query(query: str) -> Optional[str]:
    """Sanitize a query string for FTS5 MATCH syntax.

    Strips non-word, non-space characters, splits into terms, and joins with
    OR using FTS5 phrase quotes for each term. Returns None if no terms remain.

    Args:
        query: Raw user query string.

    Returns:
        FTS5 MATCH expression string, or None if the query is empty after
        sanitization.
    """
    # \w in Python re (unicode by default) matches letters, digits, underscore
    # — equivalent to \p{L}\p{N} in the JS version for typical Latin content
    cleaned = re.sub(r"[^\w\s]", " ", query, flags=re.UNICODE)
    terms = [t for t in cleaned.split() if len(t) > 1]
    if not terms:
        return None
    # Each term is double-quoted for FTS5 phrase matching; joined with OR
    return " OR ".join(f'"{t}"' for t in terms)


def _extract_matched_terms(highlighted: str) -> List[str]:
    """Extract unique matched terms from FTS5 ``highlight()`` output.

    The JS uses ``«term»`` delimiters. Returns lowercased unique terms.

    Args:
        highlighted: Output of FTS5 ``highlight(table, col, '«', '»')``.

    Returns:
        Deduplicated list of matched term strings.
    """
    matches = re.findall(r"\u00ab([^\u00bb]+)\u00bb", highlighted)
    return list(dict.fromkeys(m.lower() for m in matches))  # unique, order-preserved


def search_fts(conn: sqlite3.Connection, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Full-text search using FTS5 with BM25 ranking.

    Args:
        conn: Open database connection.
        query: Raw keyword query string.
        limit: Maximum number of results.

    Returns:
        List of result dicts with ``id``, ``content``, ``section``,
        ``chunk_index``, ``source``, ``fts_score``, ``matched_terms``.
        Empty list if no terms or if FTS fails.
    """
    fts_query = _to_fts_query(query)
    if not fts_query:
        return []

    try:
        rows = conn.execute(
            """SELECT c.id, c.content, c.section, c.chunk_index, d.source,
                      rank AS fts_score,
                      highlight(chunks_fts, 0, '\u00ab', '\u00bb') AS highlighted
               FROM chunks_fts
               JOIN chunks c ON c.id = chunks_fts.rowid
               JOIN documents d ON d.id = c.document_id
               WHERE chunks_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (fts_query, limit),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "content": row["content"],
                "section": row["section"],
                "chunk_index": row["chunk_index"],
                "source": row["source"],
                "fts_score": row["fts_score"],
                "matched_terms": _extract_matched_terms(row["highlighted"]),
            }
            for row in rows
        ]
    except Exception:  # noqa: BLE001
        return []


def search_vector(
    conn: sqlite3.Connection, query_embedding: List[float], limit: int = 10
) -> List[Dict[str, Any]]:
    """Vector similarity search using sqlite-vec KNN.

    Args:
        conn: Open database connection.
        query_embedding: Query embedding vector (must match stored dimension).
        limit: Maximum number of results.

    Returns:
        List of result dicts with ``id``, ``content``, ``section``,
        ``chunk_index``, ``source``, ``vec_distance``.
    """
    rows = conn.execute(
        """SELECT chunk_id, distance
           FROM chunks_vec
           WHERE embedding MATCH ?
           ORDER BY distance
           LIMIT ?""",
        (_to_vec_bytes(query_embedding), limit),
    ).fetchall()

    if not rows:
        return []

    ids = [row["chunk_id"] for row in rows]
    placeholders = ",".join("?" * len(ids))

    chunks = conn.execute(
        f"""SELECT c.id, c.content, c.section, c.chunk_index, d.source
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id IN ({placeholders})""",
        ids,
    ).fetchall()

    chunk_map = {row["id"]: dict(row) for row in chunks}
    dist_map = {row["chunk_id"]: row["distance"] for row in rows}

    results = []
    for row in rows:
        chunk = chunk_map.get(row["chunk_id"])
        if chunk:
            results.append({**chunk, "vec_distance": dist_map[row["chunk_id"]]})
    return results


async def hybrid_search(
    conn: sqlite3.Connection,
    query: Dict[str, str],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Run FTS5 and vector search separately, merge with Reciprocal Rank Fusion.

    The ``query`` dict must have:
    - ``keywords``: string for the BM25 full-text search
    - ``semantic``: natural-language string for the vector search

    If the vector search (embedding API) fails, the function degrades
    gracefully to FTS-only results.

    Args:
        conn: Open database connection.
        query: Dict with ``keywords`` and ``semantic`` keys.
        limit: Number of final results to return.

    Returns:
        List of merged result dicts sorted by descending RRF score.
        Each dict has ``source``, ``section``, ``content``, and optionally
        ``fts_rank``, ``vec_rank``, ``vec_distance``.
    """
    keywords = query.get("keywords", "")
    semantic = query.get("semantic", "")
    fts_limit = limit * 3

    log.search_header(keywords, semantic)

    # FTS is synchronous and always runs
    fts_results = search_fts(conn, keywords, fts_limit)
    log.search_fts(fts_results)

    # Vector search may fail if the embedding API is unavailable
    vec_results: List[Dict[str, Any]] = []
    try:
        query_embeddings = await embed(semantic)
        query_embedding = query_embeddings[0]
        vec_results = search_vector(conn, query_embedding, fts_limit)
    except Exception as exc:  # noqa: BLE001
        log.warn(f"Semantic search unavailable: {exc}")

    log.search_vec(vec_results)

    # ── Reciprocal Rank Fusion ─────────────────────────────────────────────
    # score(d) = sum over each list of 1/(k + rank)
    # A chunk appearing in both lists accumulates contributions from both.
    scores: Dict[int, Dict[str, Any]] = {}

    for rank, r in enumerate(fts_results):
        chunk_id = r["id"]
        if chunk_id not in scores:
            scores[chunk_id] = dict(r)
            scores[chunk_id]["rrf"] = 0.0
        scores[chunk_id]["rrf"] += 1.0 / (RRF_K + rank + 1)
        scores[chunk_id]["fts_rank"] = rank + 1

    for rank, r in enumerate(vec_results):
        chunk_id = r["id"]
        if chunk_id not in scores:
            scores[chunk_id] = dict(r)
            scores[chunk_id]["rrf"] = 0.0
        scores[chunk_id]["rrf"] += 1.0 / (RRF_K + rank + 1)
        scores[chunk_id]["vec_rank"] = rank + 1
        scores[chunk_id]["vec_distance"] = r.get("vec_distance")

    merged = sorted(scores.values(), key=lambda x: x["rrf"], reverse=True)[:limit]
    log.search_rrf(merged)

    # Strip internal scoring fields before returning to the agent
    return [
        {
            k: v
            for k, v in r.items()
            if k not in ("rrf", "fts_score", "id", "matched_terms")
        }
        for r in merged
    ]
