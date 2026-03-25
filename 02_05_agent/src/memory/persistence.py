# -*- coding: utf-8 -*-

#   persistence.py

"""
### Description:
Persistence helpers — write observer/reflector logs as YAML-frontmatter Markdown files.

Each log entry is stored under ``workspace/memory/`` as a numbered Markdown file
(e.g. ``observer-001.md``, ``reflector-002.md``).  The frontmatter records metadata
for post-hoc analysis; the body contains the observation text.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/memory/persistence.ts


"""

from datetime import datetime, timezone
from pathlib import Path

from ..config import MEMORY_DIR
from ..helpers.log import log, log_error


async def _persist_memory_log(
    prefix: str,
    seq: int,
    body: str,
    metadata: dict,
) -> None:
    """Write a single memory log file to disk.

    The file is created at ``MEMORY_DIR/{prefix}-{seq:03d}.md``.  The parent
    directory is created recursively if it does not exist.

    Args:
        prefix: File name prefix (``"observer"`` or ``"reflector"``).
        seq: Sequence number for this log entry.
        body: Observation text to write as the Markdown body.
        metadata: Key/value pairs written as YAML frontmatter.
    """
    filename = f"{prefix}-{seq:03d}.md"
    path = Path(MEMORY_DIR) / filename

    frontmatter_lines = "\n".join(f"{k}: {v}" for k, v in metadata.items())
    created = datetime.now(timezone.utc).isoformat()
    content = f"---\n{frontmatter_lines}\ncreated: {created}\n---\n\n{body}\n"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        log("memory", f"💾 {filename}")
    except Exception as err:
        log_error("memory", f"Failed to write {filename}:", err)


async def persist_observer_log(entry: dict) -> None:
    """Persist an observer run as a numbered log file.

    Args:
        entry: Dict with keys:
            - ``session_id`` (str)
            - ``sequence`` (int)
            - ``observations`` (str)
            - ``tokens`` (int)
            - ``messages_observed`` (int)
            - ``generation`` (int)
            - ``sealed_range`` (tuple[int, int])
    """
    start, end = entry["sealed_range"]
    await _persist_memory_log(
        "observer",
        entry["sequence"],
        entry["observations"],
        {
            "type": "observation",
            "session": entry["session_id"],
            "sequence": entry["sequence"],
            "generation": entry["generation"],
            "tokens": entry["tokens"],
            "messages_observed": entry["messages_observed"],
            "sealed_range": f"{start}–{end}",
        },
    )


async def persist_reflector_log(entry: dict) -> None:
    """Persist a reflector compression run as a numbered log file.

    Args:
        entry: Dict with keys:
            - ``session_id`` (str)
            - ``sequence`` (int)
            - ``observations`` (str)
            - ``tokens`` (int)
            - ``generation`` (int)
            - ``compression_level`` (int)
    """
    await _persist_memory_log(
        "reflector",
        entry["sequence"],
        entry["observations"],
        {
            "type": "reflection",
            "session": entry["session_id"],
            "sequence": entry["sequence"],
            "generation": entry["generation"],
            "tokens": entry["tokens"],
            "compression_level": entry["compression_level"],
        },
    )
