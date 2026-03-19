# -*- coding: utf-8 -*-

#   embeddings.py

"""
### Description:
OpenAI-compatible embeddings API wrapper. Sends texts to the configured
embeddings endpoint and returns a list of float vectors, sorted by input index.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/graph/embeddings.js`

"""

import httpx

from ..config import AI_API_KEY, EMBEDDINGS_API_ENDPOINT, EXTRA_API_HEADERS, resolve_model

MODEL = resolve_model("text-embedding-3-small")


async def embed(texts: str | list[str]) -> list[list[float]]:
    """Embed one or more texts and return their vectors.

    Always returns a list of vectors in the same order as the input.

    Args:
        texts: A single string or a list of strings to embed.

    Returns:
        List of float vectors (one per input string).

    Raises:
        RuntimeError: If the API returns an error.
    """
    input_list = texts if isinstance(texts, list) else [texts]

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            EMBEDDINGS_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            json={"model": MODEL, "input": input_list},
        )
        data = resp.json()

    if "error" in data:
        error = data["error"]
        raise RuntimeError(
            f"Embedding error: {error.get('message', str(error))}"
        )

    # Sort by index to guarantee input order (API may return out-of-order)
    return [item["embedding"] for item in sorted(data["data"], key=lambda d: d["index"])]
