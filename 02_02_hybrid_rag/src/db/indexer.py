# -*- coding: utf-8 -*-

#   indexer.py

"""
### Description:
Workspace indexer — reads .md/.txt files, chunks them, generates embeddings
in batches, and inserts everything into SQLite (documents + chunks + FTS5 +
sqlite-vec). Skips unchanged files via SHA-256 hash comparison.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/db/indexer.js

"""

import hashlib
import struct
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

from .chunking import chunk_by_separators
from .embeddings import embed
from ..helpers import logger as log

BATCH_SIZE = 20
SUPPORTED_EXTENSIONS = {".md", ".txt"}


def _hash_content(content: str) -> str:
    """Return the SHA-256 hex digest of *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _to_vec_bytes(arr: List[float]) -> bytes:
    """Serialize a float list to a packed little-endian float32 byte string.

    Args:
        arr: List of float values (embedding vector).

    Returns:
        Bytes in IEEE 754 single-precision format, compatible with sqlite-vec.
    """
    return struct.pack(f"{len(arr)}f", *arr)


def _remove_document(conn: sqlite3.Connection, doc_id: int) -> None:
    """Delete all data for a document: vec rows, chunks, document record.

    Deleting chunks triggers the FTS5 ``chunks_ad`` trigger automatically.

    Args:
        conn: Open database connection.
        doc_id: Primary key of the document to remove.
    """
    conn.execute(
        "DELETE FROM chunks_vec WHERE chunk_id IN "
        "(SELECT id FROM chunks WHERE document_id = ?)",
        (doc_id,),
    )
    conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()


async def _index_file(
    conn: sqlite3.Connection, file_path: Path, file_name: str
) -> None:
    """Index a single file: chunk → embed → insert into all tables.

    Skips the file if it is empty or if its hash matches the existing record.
    Re-indexes if the hash changed.

    Args:
        conn: Open database connection.
        file_path: Absolute path to the file.
        file_name: Relative file name used as the ``source`` identifier.
    """
    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        log.warn(f"Skipping empty file: {file_name}")
        return

    new_hash = _hash_content(content)

    existing = conn.execute(
        "SELECT id, hash FROM documents WHERE source = ?", (file_name,)
    ).fetchone()

    if existing and existing["hash"] == new_hash:
        log.info(f"Skipping {file_name} (unchanged)")
        return

    if existing:
        log.info(f"Re-indexing {file_name} (changed)")
        _remove_document(conn, existing["id"])

    # 1. Chunk
    chunks = chunk_by_separators(content, source=file_name)
    log.info(f"{file_name}: {len(chunks)} chunks")

    # 2. Insert document record
    cursor = conn.execute(
        "INSERT INTO documents (source, content, hash) VALUES (?, ?, ?)",
        (file_name, content, new_hash),
    )
    doc_id = cursor.lastrowid
    conn.commit()

    # 3. Insert chunks (the chunks_ai trigger populates FTS5 automatically)
    chunk_ids: List[int] = []
    for chunk in chunks:
        cursor = conn.execute(
            "INSERT INTO chunks (document_id, content, chunk_index, section, chars) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                doc_id,
                chunk["content"],
                chunk["metadata"]["index"],
                chunk["metadata"]["section"],
                chunk["metadata"]["chars"],
            ),
        )
        chunk_ids.append(cursor.lastrowid)
    conn.commit()

    # 4. Generate embeddings in batches (to respect API rate limits)
    contents = [c["content"] for c in chunks]
    all_embeddings: List[List[float]] = []

    for i in range(0, len(contents), BATCH_SIZE):
        batch = contents[i: i + BATCH_SIZE]
        batch_embeddings = await embed(batch)
        all_embeddings.extend(batch_embeddings)
        sys.stdout.write(f"  embeddings: {len(all_embeddings)}/{len(contents)}\r")
        sys.stdout.flush()

    if len(contents) > BATCH_SIZE:
        print()

    # 5. Insert vector rows
    for chunk_id, embedding in zip(chunk_ids, all_embeddings):
        conn.execute(
            "INSERT INTO chunks_vec (chunk_id, embedding) VALUES (?, ?)",
            (chunk_id, _to_vec_bytes(embedding)),
        )
    conn.commit()

    log.success(f"Indexed {file_name}: {len(chunks)} chunks")


async def index_workspace(conn: sqlite3.Connection, workspace_path: str) -> None:
    """Index all .md/.txt files in *workspace_path*.

    Skips unchanged files and removes stale entries for files deleted from disk.

    Args:
        conn: Open database connection.
        workspace_path: Path to the workspace directory (relative or absolute).
    """
    workspace = Path(workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)

    files = [
        f for f in workspace.iterdir()
        if f.is_file() and f.suffix in SUPPORTED_EXTENSIONS
    ]

    if not files:
        log.warn(f"No .md/.txt files found in {workspace_path}")
        return

    log.info(f"Found {len(files)} file(s) in {workspace_path}")

    for file_path in sorted(files):
        await _index_file(conn, file_path, file_path.name)

    # Prune stale documents (files deleted from workspace)
    indexed = conn.execute("SELECT id, source FROM documents").fetchall()
    on_disk = {f.name for f in files}

    for doc in indexed:
        if doc["source"] not in on_disk:
            log.info(f"Removing stale index: {doc['source']}")
            _remove_document(conn, doc["id"])
