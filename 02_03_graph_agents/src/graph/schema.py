# -*- coding: utf-8 -*-

#   schema.py

"""
### Description:
Graph schema setup — creates uniqueness constraints, full-text indexes, and
vector indexes in Neo4j. All statements are idempotent via ``IF NOT EXISTS``.

Node labels:    Document, Chunk, Entity
Relationships:  HAS_CHUNK, MENTIONS, RELATED_TO

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/graph/schema.js`

"""

from neo4j import AsyncDriver

from .driver import write_query
from ..helpers.logger import log

EMBEDDING_DIM = 1536  # openai/text-embedding-3-small

_SETUP_STATEMENTS = [
    # ── Uniqueness constraints ────────────────────────────────────────────────
    """CREATE CONSTRAINT doc_source IF NOT EXISTS
       FOR (d:Document) REQUIRE d.source IS UNIQUE""",

    """CREATE CONSTRAINT entity_name_type IF NOT EXISTS
       FOR (e:Entity) REQUIRE (e.name, e.type) IS UNIQUE""",

    # ── Full-text indexes ─────────────────────────────────────────────────────
    """CREATE FULLTEXT INDEX chunk_content_ft IF NOT EXISTS
       FOR (c:Chunk) ON EACH [c.content]""",

    """CREATE FULLTEXT INDEX entity_name_ft IF NOT EXISTS
       FOR (e:Entity) ON EACH [e.name, e.aliases_text]""",

    # ── Vector indexes ────────────────────────────────────────────────────────
    f"""CREATE VECTOR INDEX chunk_embedding_vec IF NOT EXISTS
       FOR (c:Chunk) ON (c.embedding)
       OPTIONS {{indexConfig: {{
         `vector.dimensions`: {EMBEDDING_DIM},
         `vector.similarity_function`: 'cosine'
       }}}}""",

    f"""CREATE VECTOR INDEX entity_embedding_vec IF NOT EXISTS
       FOR (e:Entity) ON (e.embedding)
       OPTIONS {{indexConfig: {{
         `vector.dimensions`: {EMBEDDING_DIM},
         `vector.similarity_function`: 'cosine'
       }}}}""",
]

# ── Label / relationship name constants ───────────────────────────────────────

class Labels:
    Document = "Document"
    Chunk = "Chunk"
    Entity = "Entity"


class Rels:
    HAS_CHUNK = "HAS_CHUNK"
    MENTIONS = "MENTIONS"
    RELATED_TO = "RELATED_TO"


async def ensure_schema(driver: AsyncDriver) -> None:
    """Create all constraints and indexes if they don't exist.

    Each statement is run independently so a single failure does not block
    the rest. ``IF NOT EXISTS`` makes every statement idempotent.

    Args:
        driver: Neo4j async driver.
    """
    for stmt in _SETUP_STATEMENTS:
        try:
            await write_query(driver, stmt)
        except Exception as err:
            msg = str(err)
            # Some Neo4j editions raise on duplicate — safe to ignore
            if "equivalent index already exists" in msg:
                continue
            log.warn(f"Schema statement skipped: {msg.splitlines()[0]}")

    log.success("Graph schema ready")
