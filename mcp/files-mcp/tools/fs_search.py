# -*- coding: utf-8 -*-

#   fs_search.py

"""
### Description:
fs_search MCP tool — find files by name or search file content within the sandbox.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from lib.filetypes import is_text_file, matches_glob, matches_type
from lib.ignore import create_ignore_matcher
from lib.paths import rel, resolve_safe
from lib.search import search_files
from utils.errors import OUT_OF_SCOPE_ERROR


def fs_search(
    path: str,
    query: str,
    target: str = "all",
    patternMode: str = "literal",
    caseInsensitive: bool = False,
    depth: int = 5,
    maxResults: int = 100,
    wholeWord: bool = False,
    multiline: bool = False,
    types: Optional[list[str]] = None,
    glob: Optional[str] = None,
    exclude: Optional[list[str]] = None,
    respectIgnore: bool = False,
) -> str:
    """Find files by name or search file content within the sandbox.

    Args:
        path: Starting directory within sandbox (``"."`` for root).
        query: Search term.
        target: ``"all"`` | ``"filename"`` | ``"content"``.
        patternMode: ``"literal"`` | ``"regex"`` | ``"fuzzy"``.
        caseInsensitive: Case-insensitive matching.
        depth: Maximum directory depth to traverse.
        maxResults: Maximum number of results to return.
        wholeWord: Match whole words only (wraps pattern with ``\\b``).
        multiline: Enable multiline matching (dot matches newline).
        types: Filter files by type (e.g. ``["py", "js"]``).
        glob: Glob pattern to include files (e.g. ``"*.py"``).
        exclude: Glob patterns to exclude.
        respectIgnore: Skip files matched by .gitignore.

    Returns:
        JSON-encoded result dict.
    """
    resolved = resolve_safe(path)
    if resolved is None:
        return json.dumps(OUT_OF_SCOPE_ERROR)
    if not resolved.is_dir():
        return json.dumps({"success": False, "error": f"Not a directory: {path}"})

    # --- Fuzzy filename search delegates to scored lib/search.py ---
    if patternMode == "fuzzy" and target in ("all", "filename"):
        results = search_files(resolved, query, case_insensitive=caseInsensitive, max_results=maxResults)
        file_matches = [{"name": m.name, "path": m.path, "score": m.score} for m in results]
        return json.dumps({
            "success": True,
            "query": query,
            "files": file_matches,
            "content": [],
            "totalCount": len(file_matches),
            "truncated": False,
        })

    flags = re.IGNORECASE if caseInsensitive else 0
    if multiline:
        flags |= re.DOTALL

    if patternMode == "regex":
        raw_pattern = rf"\b(?:{query})\b" if wholeWord else query
        try:
            pattern = re.compile(raw_pattern, flags)
        except re.error as exc:
            return json.dumps({"success": False, "error": f"Invalid regex: {exc}"})
    elif patternMode == "fuzzy":
        chars = ".*".join(re.escape(c) for c in query)
        raw_pattern = rf"\b(?:{chars})\b" if wholeWord else chars
        pattern = re.compile(raw_pattern, flags)
    else:
        escaped = re.escape(query)
        raw_pattern = rf"\b{escaped}\b" if wholeWord else escaped
        pattern = re.compile(raw_pattern, flags)

    glob_patterns = [glob] if glob else None
    is_ignored = create_ignore_matcher(resolved) if respectIgnore else (lambda _: False)

    file_matches: list[dict[str, str]] = []
    content_matches: list[dict[str, Any]] = []
    total_count = 0
    truncated = False

    def _walk(dirpath: Path, current_depth: int) -> None:
        nonlocal total_count, truncated
        if current_depth > depth:
            return
        try:
            items = sorted(dirpath.iterdir(), key=lambda p: p.name.lower())
        except PermissionError:
            return
        for item in items:
            if total_count >= maxResults:
                truncated = True
                return
            if is_ignored(item):
                continue
            if exclude and matches_glob(item, exclude):
                continue
            if item.is_dir():
                _walk(item, current_depth + 1)
            elif item.is_file():
                if types and not matches_type(item, types):
                    continue
                if glob_patterns and not matches_glob(item, glob_patterns):
                    continue

                matched_name = False
                if target in ("all", "filename") and pattern.search(item.name):
                    file_matches.append({"name": item.name, "path": rel(item)})
                    total_count += 1
                    matched_name = True

                if target in ("all", "content") and not matched_name and is_text_file(item):
                    try:
                        for lineno, line in enumerate(
                            item.read_text(encoding="utf-8", errors="replace").splitlines(),
                            start=1,
                        ):
                            if total_count >= maxResults:
                                truncated = True
                                break
                            if pattern.search(line):
                                content_matches.append({
                                    "path": rel(item),
                                    "line": lineno,
                                    "text": line.rstrip(),
                                })
                                total_count += 1
                    except OSError:
                        pass

    _walk(resolved, current_depth=1)

    return json.dumps({
        "success": True,
        "query": query,
        "files": file_matches,
        "content": content_matches,
        "totalCount": total_count,
        "truncated": truncated,
        **({"hint": f"Results truncated at {maxResults}. Use 'path' to narrow scope or increase 'maxResults'."} if truncated else {}),
    })
