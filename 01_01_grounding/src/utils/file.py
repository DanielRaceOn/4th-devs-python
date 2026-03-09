# -*- coding: utf-8 -*-

#   file.py

"""
### Description:
File system helpers: directory creation, JSON read/write with atomic rename,
and markdown file resolution from the notes directory.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `src/utils/file.js`

"""

import json
import os
from pathlib import Path
from typing import Any


async def ensure_dir(dir_path: Path) -> None:
    """Create ``dir_path`` and all parents if they do not exist.

    Args:
        dir_path: Directory path to create.
    """
    dir_path.mkdir(parents=True, exist_ok=True)


async def resolve_markdown_path(notes_dir: Path, input_file: str | None) -> Path:
    """Resolve the markdown file to process.

    If ``input_file`` is given, it is resolved relative to ``notes_dir``
    (or used as-is if absolute). Otherwise the first ``.md`` file found in
    ``notes_dir`` (sorted alphabetically) is returned.

    Args:
        notes_dir: Directory containing markdown note files.
        input_file: Optional filename or absolute path provided by the user.

    Returns:
        Absolute ``Path`` to the markdown file.

    Raises:
        ValueError: If ``input_file`` does not end with ``.md``.
        FileNotFoundError: If the resolved file does not exist, or no ``.md``
            files are found in ``notes_dir``.
    """
    await ensure_dir(notes_dir)

    if input_file:
        candidate = Path(input_file) if Path(input_file).is_absolute() else notes_dir / input_file
        if not str(candidate).endswith(".md"):
            raise ValueError("Please provide a .md file name.")
        if not candidate.exists():
            raise FileNotFoundError(f"File not found: {candidate}")
        return candidate

    md_files = sorted(p.name for p in notes_dir.iterdir() if p.is_file() and p.suffix == ".md")
    if not md_files:
        raise FileNotFoundError(
            f"No .md files found in {notes_dir}. Add a markdown file to process."
        )
    return notes_dir / md_files[0]


async def read_json_if_exists(file_path: Path) -> Any:
    """Read and parse a JSON file, returning ``None`` if it does not exist.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed JSON value, or ``None`` if the file is absent.

    Raises:
        Exception: Re-raises any error other than ``FileNotFoundError``.
    """
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


async def safe_write_json(file_path: Path, data: Any) -> None:
    """Atomically write ``data`` as formatted JSON to ``file_path``.

    Writes to a ``.tmp`` sibling file first, then renames for atomicity.

    Args:
        file_path: Destination path for the JSON file.
        data: JSON-serialisable value to write.
    """
    await ensure_dir(file_path.parent)
    temp_path = Path(str(file_path) + ".tmp")
    temp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temp_path, file_path)
