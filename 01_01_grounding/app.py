# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Entry point for the 01_01_grounding lesson module. Runs the four-stage pipeline:
extract → dedupe → search → ground, transforming markdown notes into interactive
HTML annotated with fact-checked, source-backed concept tooltips.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `app.js`

"""

import asyncio
import logging
import sys

from src.config import paths, cli
from src.utils.file import resolve_markdown_path
from src.utils.text import split_paragraphs
from src.pipeline.extract import extract_concepts
from src.pipeline.dedupe import dedupe_concepts
from src.pipeline.search import search_concepts
from src.pipeline.ground import generate_and_apply_template

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def _confirm_run() -> None:
    print()
    print("⚠️  UWAGA: Uruchomienie tego skryptu może zużyć znaczną ilość tokenów.")
    print("   Jeśli nie chcesz go uruchamiać, możesz sprawdzić gotowy wynik w pliku:")
    print("   01_01_grounding/output/grounded_demo.html")
    print()
    answer = input("Czy chcesz kontynuować? (yes/y): ").strip().lower()
    if answer not in ("yes", "y"):
        print("Przerwano.")
        sys.exit(0)


async def main() -> None:
    """Run the full grounding pipeline."""
    await _confirm_run()

    source_file = await resolve_markdown_path(paths["notes"], cli["input_file"])
    markdown = source_file.read_text(encoding="utf-8")
    paragraphs = split_paragraphs(markdown)

    print(f"\n📄 Source: {source_file}")
    print(f"   Paragraphs: {len(paragraphs)}\n")

    print("1. Extracting concepts...")
    concepts_data = await extract_concepts(paragraphs, source_file)
    print(f"   Total: {concepts_data['conceptCount']} concepts\n")

    print("2. Deduplicating concepts...")
    dedupe_data = await dedupe_concepts(concepts_data)
    print(f"   Groups: {len(dedupe_data['groups'])}\n")

    print("3. Web search grounding...")
    search_data = await search_concepts(concepts_data, dedupe_data)
    print(f"   Results: {len(search_data['resultsByCanonical'])}\n")

    print("4. Generating HTML...")
    if cli["force"] or not paths["grounded"].exists():
        await generate_and_apply_template(markdown, concepts_data, dedupe_data, search_data)
        print(f"   Created: {paths['grounded']}\n")
    else:
        print("   Skipped (exists, use --force to regenerate)\n")

    print("✅ Done! Output files:")
    print(f"   {paths['concepts']}")
    print(f"   {paths['dedupe']}")
    print(f"   {paths['search']}")
    print(f"   {paths['grounded']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
