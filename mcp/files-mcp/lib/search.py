# -*- coding: utf-8 -*-

#   search.py

"""
### Description:
Fuzzy filename search with scoring — exact > prefix > contains > fuzzy.

---

@Author:        Daniel Szczepanski
@Created on:    26.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lib.paths import rel


@dataclass
class ScoredMatch:
    """A file match with a relevance score.

    Attributes:
        path: Relative POSIX path within the sandbox.
        name: File name.
        score: Relevance score (higher = better). Tiers:
            100 = exact name match,
            80  = prefix match,
            60  = contains match,
            40  = fuzzy (all chars appear in order).
    """

    path: str
    name: str
    score: int


def search_files(
    root: Path,
    query: str,
    *,
    case_insensitive: bool = True,
    max_results: int = 50,
) -> list[ScoredMatch]:
    """Search for files whose names match ``query`` with scored ranking.

    Scoring tiers (descending priority):
    - **Exact**: filename == query → 100
    - **Prefix**: filename starts with query → 80
    - **Contains**: query is a substring of filename → 60
    - **Fuzzy**: all chars of query appear in order in filename → 40

    Args:
        root: Directory to search recursively.
        query: Search string.
        case_insensitive: Fold case before comparing.
        max_results: Maximum matches to return.

    Returns:
        List of ``ScoredMatch`` objects sorted by score descending, then name.
    """
    q = query.lower() if case_insensitive else query
    fuzzy_re = re.compile(".*".join(re.escape(c) for c in q))

    matches: list[ScoredMatch] = []
    for item in root.rglob("*"):
        if not item.is_file():
            continue
        name = item.name
        compare = name.lower() if case_insensitive else name

        if compare == q:
            score = 100
        elif compare.startswith(q):
            score = 80
        elif q in compare:
            score = 60
        elif fuzzy_re.search(compare):
            score = 40
        else:
            continue

        matches.append(ScoredMatch(path=rel(item), name=name, score=score))
        if len(matches) >= max_results * 3:  # gather extra for sorting
            break

    matches.sort(key=lambda m: (-m.score, m.name))
    return matches[:max_results]
