# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Runs all four chunking strategies on workspace/example.md and saves results
as JSONL files to workspace/. Prompts the user before running LLM-dependent
strategies to avoid unintended token usage.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      app.js

"""

import asyncio
import json
import sys
from pathlib import Path

from src.strategies.characters import chunk_by_characters
from src.strategies.separators import chunk_by_separators
from src.strategies.context import chunk_with_context
from src.strategies.topics import chunk_by_topics

_MODULE_DIR = Path(__file__).parent
INPUT = _MODULE_DIR / "workspace" / "example.md"
WORKSPACE_DIR = _MODULE_DIR / "workspace"


def _confirm_run() -> None:
    """Prompt the user for confirmation before spending tokens.

    Exits immediately with code 0 if the user declines.
    """
    print("\n⚠️  UWAGA: Uruchomienie tego przykładu zużyje tokeny (strategie context i topics używają LLM).")
    print("   Jeśli nie chcesz uruchamiać go teraz, najpierw sprawdź gotowe wyniki:")
    print(f"   Demo: {WORKSPACE_DIR}/example-*.jsonl")
    print()

    try:
        answer = input("Czy chcesz kontynuować? (yes/y): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nPrzerwano.")
        sys.exit(0)

    if answer not in ("yes", "y"):
        print("Przerwano.")
        sys.exit(0)


def _to_jsonl(chunks: list) -> str:
    """Serialize a list of chunk dicts to a JSONL string (one JSON object per line)."""
    return "\n".join(json.dumps(chunk, ensure_ascii=False) for chunk in chunks)


def _save(name: str, chunks: list) -> None:
    """Write chunks to ``workspace/example-{name}.jsonl``.

    Args:
        name: Strategy name suffix for the output filename.
        chunks: List of chunk dicts to serialize.
    """
    path = WORKSPACE_DIR / f"example-{name}.jsonl"
    path.write_text(_to_jsonl(chunks), encoding="utf-8")
    print(f"  \u2713 {path.relative_to(_MODULE_DIR)} ({len(chunks)} chunks)")


async def main() -> None:
    """Orchestrate all four chunking strategies and save their JSONL outputs."""
    _confirm_run()

    text = INPUT.read_text(encoding="utf-8")
    source = str(INPUT.relative_to(_MODULE_DIR))
    print(f"Source: {source} ({len(text)} chars)\n")

    print("1. Characters...")
    _save("characters", chunk_by_characters(text))

    print("2. Separators...")
    _save("separators", chunk_by_separators(text, source=source))

    print("3. Context (LLM-enriched)...")
    _save("context", await chunk_with_context(text, source=source))

    print("4. Topics (AI-driven)...")
    _save("topics", await chunk_by_topics(text, source=source))

    print("\nDone.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrzerwano.")
        sys.exit(0)
