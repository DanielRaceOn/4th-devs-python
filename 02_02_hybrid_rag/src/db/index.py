# -*- coding: utf-8 -*-

#   index.py

"""
### Description:
SQLite database initializer with FTS5 (full-text search) and sqlite-vec
(vector similarity search) virtual tables. Creates the schema on first run
and returns the connection for use by the indexer and search modules.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/db/index.js

"""

import sqlite3
from pathlib import Path

import sqlite_vec  # pip install sqlite-vec

from ..helpers import logger as log

EMBEDDING_DIM = 1536  # openai/text-embedding-3-small


def init_db(db_path: str = "data/hybrid.db") -> sqlite3.Connection:
    """Open (or create) the SQLite database and initialize the full schema.

    Creates:
    - ``documents`` table (source, content, hash, indexed_at)
    - ``chunks`` table (document_id FK, content, chunk_index, section, chars)
    - ``chunks_fts`` virtual table (FTS5 external-content backed by chunks)
    - Triggers ``chunks_ai``, ``chunks_ad``, ``chunks_au`` to keep FTS5 in sync
    - ``chunks_vec`` virtual table (sqlite-vec, float[1536])

    Args:
        db_path: Path to the SQLite database file (created if missing).

    Returns:
        Open ``sqlite3.Connection`` with WAL mode and foreign keys enabled.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # check_same_thread=False is required because the async agent loop may call
    # sqlite from different threads via run_in_executor
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row  # dict-like access by column name

    # sqlite-vec calls load_extension() internally, so we must enable it first.
    # enable_load_extension is disabled by default for security reasons.
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)  # re-disable after loading

    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.commit()

    # Verify the extension loaded correctly
    version = conn.execute("SELECT vec_version() AS v").fetchone()["v"]
    log.info(f"sqlite-vec {version}")

    conn.executescript(f"""
        CREATE TABLE IF NOT EXISTS documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL UNIQUE,
            content     TEXT NOT NULL,
            hash        TEXT NOT NULL,
            indexed_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            content     TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            section     TEXT,
            chars       INTEGER NOT NULL
        );

        -- FTS5 external-content table backed by the chunks table.
        -- "external-content" means FTS5 does NOT store a copy of the text —
        -- it references chunks.content via rowid for reads.
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            content,
            content='chunks',
            content_rowid='id'
        );

        -- Triggers keep the FTS5 index in sync whenever chunks are modified.
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, content)
            VALUES ('delete', old.id, old.content);
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, content)
            VALUES ('delete', old.id, old.content);
            INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
        END;

        -- sqlite-vec virtual table for L2/cosine vector search.
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding float[{EMBEDDING_DIM}]
        );
    """)
    conn.commit()

    return conn
