# -*- coding: utf-8 -*-

#   embeddings.py

"""
### Description:
OpenAI Embeddings API wrapper. Accepts a list of texts, sends them as a
batch, and returns embeddings sorted by index (matching input order).

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/db/embeddings.js

"""

from typing import Any, Dict, List, Union

import httpx

from ..config import AI_API_KEY, EMBEDDINGS_API_ENDPOINT, EXTRA_API_HEADERS, resolve_model

MODEL: str = resolve_model("text-embedding-3-small")


async def embed(texts: Union[str, List[str]]) -> List[List[float]]:
    """Fetch embeddings for one or more texts.

    Args:
        texts: A single text string or list of strings. A single string is
            automatically wrapped in a list and the result unwrapped is NOT
            done — the caller always receives a list of embedding vectors.

    Returns:
        List of embedding vectors (each a list of floats), sorted by the
        original input order.

    Raises:
        RuntimeError: If the API returns an error.
    """
    input_list = [texts] if isinstance(texts, str) else texts

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            EMBEDDINGS_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            json={"model": MODEL, "input": input_list},
        )

    data: Dict[str, Any] = response.json()

    if data.get("error"):
        err = data["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise RuntimeError(f"Embedding error: {msg}")

    # Sort by index to guarantee output matches input order
    items: List[Dict[str, Any]] = sorted(data["data"], key=lambda d: d["index"])
    return [item["embedding"] for item in items]
