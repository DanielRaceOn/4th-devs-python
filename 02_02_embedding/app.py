# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Interactive REPL for demonstrating text embeddings and cosine similarity.
After each new entry, prints a color-coded N×N pairwise similarity matrix.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      app.js

"""

import asyncio
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv

# ── stdout encoding (Windows cp1252 cannot render █ or ANSI) ──────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Config (inlined — no separate config.py needed for a single-file module) ──

_ROOT_DIR = Path(__file__).parent.parent  # project root where .env lives
_ROOT_ENV_FILE = _ROOT_DIR / ".env"

_EMBEDDINGS_ENDPOINTS: Dict[str, str] = {
    "openai": "https://api.openai.com/v1/embeddings",
    "openrouter": "https://openrouter.ai/api/v1/embeddings",
}
_VALID_PROVIDERS = {"openai", "openrouter"}

if _ROOT_ENV_FILE.exists():
    load_dotenv(_ROOT_ENV_FILE)

_OPENAI_API_KEY: str = (os.environ.get("OPENAI_API_KEY") or "").strip()
_OPENROUTER_API_KEY: str = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
_requested_provider: str = (os.environ.get("AI_PROVIDER") or "").strip().lower()

_has_openai_key = bool(_OPENAI_API_KEY)
_has_openrouter_key = bool(_OPENROUTER_API_KEY)

if not _has_openai_key and not _has_openrouter_key:
    print("\033[31mError: API key is not set\033[0m", file=sys.stderr)
    print(f"       Create: {_ROOT_ENV_FILE}", file=sys.stderr)
    print("       Add one of:", file=sys.stderr)
    print("       OPENAI_API_KEY=sk-...", file=sys.stderr)
    print("       OPENROUTER_API_KEY=sk-or-v1-...", file=sys.stderr)
    sys.exit(1)

if _requested_provider and _requested_provider not in _VALID_PROVIDERS:
    print(
        "\033[31mError: AI_PROVIDER must be one of: openai, openrouter\033[0m",
        file=sys.stderr,
    )
    sys.exit(1)


def _resolve_provider() -> str:
    if _requested_provider:
        if _requested_provider == "openai" and not _has_openai_key:
            print(
                "\033[31mError: AI_PROVIDER=openai requires OPENAI_API_KEY\033[0m",
                file=sys.stderr,
            )
            sys.exit(1)
        if _requested_provider == "openrouter" and not _has_openrouter_key:
            print(
                "\033[31mError: AI_PROVIDER=openrouter requires OPENROUTER_API_KEY\033[0m",
                file=sys.stderr,
            )
            sys.exit(1)
        return _requested_provider
    return "openai" if _has_openai_key else "openrouter"


_AI_PROVIDER: str = _resolve_provider()
_AI_API_KEY: str = _OPENAI_API_KEY if _AI_PROVIDER == "openai" else _OPENROUTER_API_KEY
EMBEDDINGS_API_ENDPOINT: str = _EMBEDDINGS_ENDPOINTS[_AI_PROVIDER]

_EXTRA_API_HEADERS: Dict[str, str] = {}
if _AI_PROVIDER == "openrouter":
    _referer = (os.environ.get("OPENROUTER_HTTP_REFERER") or "").strip()
    _app_name = (os.environ.get("OPENROUTER_APP_NAME") or "").strip()
    if _referer:
        _EXTRA_API_HEADERS["HTTP-Referer"] = _referer
    if _app_name:
        _EXTRA_API_HEADERS["X-Title"] = _app_name


def _resolve_model_for_provider(model: str) -> str:
    """Return the model identifier adjusted for the active provider.

    Args:
        model: Base model name, e.g. ``'text-embedding-3-small'``.

    Returns:
        Model string ready to send to the API. For OpenRouter, prepends
        ``openai/`` when no ``/`` is present in the model name.
    """
    if _AI_PROVIDER != "openrouter" or "/" in model:
        return model
    return f"openai/{model}"


MODEL: str = _resolve_model_for_provider("text-embedding-3-small")

# ── ANSI colors ───────────────────────────────────────────────────────────────

_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"


def _color_for(score: float) -> str:
    """Return the ANSI color code for a given similarity score.

    Args:
        score: Cosine similarity value in [0, 1].

    Returns:
        ANSI escape sequence: green (>=0.60), yellow (>=0.35), red (<0.35).
    """
    if score >= 0.6:
        return _GREEN
    if score >= 0.35:
        return _YELLOW
    return _RED


# ── Embedding API ─────────────────────────────────────────────────────────────


async def embed(text: str) -> List[float]:
    """Fetch the embedding vector for a text string from the embeddings API.

    Args:
        text: The input string to embed.

    Returns:
        List of floats representing the embedding vector.

    Raises:
        RuntimeError: If the API returns an error response.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            EMBEDDINGS_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_AI_API_KEY}",
                **_EXTRA_API_HEADERS,
            },
            json={"model": MODEL, "input": text},
            timeout=60.0,
        )

    data: Dict[str, Any] = response.json()

    if data.get("error"):
        error = data["error"]
        message = (
            error.get("message") if isinstance(error, dict) else str(error)
        ) or str(error)
        raise RuntimeError(message)

    return data["data"][0]["embedding"]  # type: ignore[index]


# ── Math ──────────────────────────────────────────────────────────────────────


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two equal-length vectors.

    Manual dot product — no numpy required.

    Args:
        a: First embedding vector.
        b: Second embedding vector.

    Returns:
        Cosine similarity score in [-1, 1].
    """
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for ai, bi in zip(a, b):
        dot += ai * bi
        norm_a += ai * ai
        norm_b += bi * bi
    denom = math.sqrt(norm_a) * math.sqrt(norm_b)
    return dot / denom if denom > 0 else 0.0


# ── Display ───────────────────────────────────────────────────────────────────

_LABEL_WIDTH = 14


def _truncate(text: str, width: int) -> str:
    """Truncate *text* to *width* chars, appending ellipsis if needed."""
    if len(text) > width:
        return text[: width - 1] + "\u2026"
    return text


def preview(embedding: List[float]) -> str:
    """Format a short human-readable preview of an embedding vector.

    Args:
        embedding: The full embedding vector.

    Returns:
        Formatted string showing first 4 + last 2 dimensions and total length.
    """
    head = ", ".join(f"{v:.4f}" for v in embedding[:4])
    tail = ", ".join(f"{v:.4f}" for v in embedding[-2:])
    return (
        f"{_DIM}[{head}, \u2026, {tail}]{_RESET} "
        f"{_CYAN}({len(embedding)}d){_RESET}"
    )


def print_matrix(entries: List[Dict[str, Any]]) -> None:
    """Print the full N×N pairwise cosine similarity matrix to stdout.

    Diagonal cells show ``——``. Off-diagonal cells show a bar of ``█``
    characters (length = round(score * 8)) plus the numeric score, colored
    green (>=0.60), yellow (>=0.35), or red (<0.35). Labels are truncated
    to 14 characters.

    Args:
        entries: List of dicts with ``text`` (str) and ``embedding``
            (list[float]).
    """
    labels = [_truncate(e["text"], _LABEL_WIDTH) for e in entries]
    col_width = max(_LABEL_WIDTH, max(len(lb) for lb in labels)) + 1

    # Header row — pad label area then right-justify each column header
    header_pad = " " * (_LABEL_WIDTH + 2)
    header_cells = "".join(
        f"{_BOLD}{lb.rjust(col_width)}{_RESET}" for lb in labels
    )
    print(f"\n{header_pad}{header_cells}")

    # Matrix rows
    for i, entry_i in enumerate(entries):
        row_label = f"{_BOLD}{labels[i].ljust(_LABEL_WIDTH)}{_RESET}  "
        cells: List[str] = []

        for j, entry_j in enumerate(entries):
            if i == j:
                # Diagonal: dim em-dashes
                visible = "  \u2014\u2014"
                padding = " " * (col_width - len(visible))
                cells.append(f"{padding}{_DIM}{visible}{_RESET}")
            else:
                score = cosine_similarity(entry_i["embedding"], entry_j["embedding"])
                color = _color_for(score)
                bar = "\u2588" * round(score * 8)
                value = f"{score:.2f}"
                # Measure visible content length for correct right-padding
                visible_content = f"{bar} {value}"
                padding = " " * (col_width - len(visible_content))
                cells.append(f"{padding}{color}{visible_content}{_RESET}")

        print(row_label + "".join(cells))

    # Legend
    print(
        f"\n  {_DIM}Legend:{_RESET} "
        f"{_GREEN}\u2588\u2588\u2588 \u22650.60 similar{_RESET}  "
        f"{_YELLOW}\u2588\u2588\u2588 \u22650.35 related{_RESET}  "
        f"{_RED}\u2588\u2588\u2588 <0.35 distant{_RESET}"
    )


# ── REPL ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    """Run the interactive embedding REPL."""
    loop = asyncio.get_event_loop()
    entries: List[Dict[str, Any]] = []

    print(f"\n{_CYAN}Embedding + Similarity Matrix{_RESET} (model: {MODEL})")
    print("Type 'exit' or press Enter to quit.\n")

    while True:
        try:
            # run_in_executor prevents blocking the async event loop on input()
            user_input: str = await loop.run_in_executor(
                None, lambda: input("Text: ")
            )
        except (EOFError, KeyboardInterrupt):
            break

        text = user_input.strip()
        if not text or text.lower() == "exit":
            break

        try:
            embedding = await embed(text)
            entries.append({"text": text, "embedding": embedding})

            print(f'\n  "{text}" \u2192 {preview(embedding)}')

            if len(entries) == 1:
                print(f"{_DIM}  Add more entries to see the similarity matrix.{_RESET}")
                print()
                continue

            print_matrix(entries)
            print()

        except Exception as exc:  # noqa: BLE001
            print(f"\033[31mError: {exc}\033[0m\n", file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
