# -*- coding: utf-8 -*-

#   context.py

"""
### Description:
Context-enriched chunking strategy (Anthropic-style contextual retrieval).
Splits the document with the separator strategy first, then calls the LLM
once per chunk to generate a 1-2 sentence contextual summary that situates
the chunk within the overall document.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/strategies/context.js

"""

import sys
from typing import Dict, List, Optional

from ..api import chat
from .separators import chunk_by_separators

_CONTEXT_INSTRUCTIONS = (
    "Generate a very short (1-2 sentence) context that situates this chunk "
    "within the overall document. Return ONLY the context, nothing else."
)


async def _enrich_chunk(chunk: Dict) -> Dict:
    """Call the LLM to generate a contextual summary for a single chunk.

    Args:
        chunk: A separator-strategy chunk dict with ``content`` and ``metadata``.

    Returns:
        New chunk dict with ``metadata.strategy`` set to ``"context"`` and
        ``metadata.context`` populated with the LLM-generated summary.
    """
    context = await chat(
        f"<chunk>{chunk['content']}</chunk>",
        _CONTEXT_INSTRUCTIONS,
    )
    return {
        "content": chunk["content"],
        "metadata": {**chunk["metadata"], "strategy": "context", "context": context},
    }


async def chunk_with_context(
    text: str,
    source: Optional[str] = None,
) -> List[Dict]:
    """Split *text* with separators then enrich each chunk with LLM context.

    Processes chunks sequentially (one LLM call per chunk) and prints progress
    to stdout. This is the most token-intensive strategy.

    Args:
        text: Full source document text.
        source: Optional source file path stored in chunk metadata.

    Returns:
        List of context-enriched chunk dicts.
    """
    base_chunks = chunk_by_separators(text, source=source)
    enriched: List[Dict] = []

    for i, chunk in enumerate(base_chunks):
        # \r overwrites the same line for a compact live progress display
        sys.stdout.write(f"  context: enriching {i + 1}/{len(base_chunks)}\r")
        sys.stdout.flush()
        enriched.append(await _enrich_chunk(chunk))

    print()  # newline after the \r progress line
    return enriched
