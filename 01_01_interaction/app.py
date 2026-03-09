# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Multi-turn conversation example using the Responses API with full input history.
Sends an initial question, then a follow-up with the prior exchange as context,
and prints both answers along with reasoning token counts.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `app.js`

"""

import asyncio
import sys
from typing import Any

import httpx

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT, resolve_model_for_provider  # noqa: E402
from helpers import extract_response_text, to_message  # noqa: E402

MODEL = resolve_model_for_provider("gpt-5.2")


async def chat(
    input_text: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send a message to the Responses API, optionally with conversation history.

    Args:
        input_text: The user's message text.
        history: Previous conversation turns to include as context.

    Returns:
        Dict with ``text`` (str) and ``reasoning_tokens`` (int).

    Raises:
        RuntimeError: If the API returns an error or no text output.
    """
    if history is None:
        history = []

    payload = {
        "model": MODEL,
        "input": [*history, to_message("user", input_text)],
        "reasoning": {"effort": "medium"},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RESPONSES_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            json=payload,
            timeout=120.0,
        )

    data = response.json()

    if not response.is_success or data.get("error"):
        message = (
            data.get("error", {}).get("message")
            or f"Request failed with status {response.status_code}"
        )
        raise RuntimeError(message)

    text = extract_response_text(data)
    if not text:
        raise RuntimeError("Missing text output in API response")

    reasoning_tokens: int = (
        data.get("usage", {})
        .get("output_tokens_details", {})
        .get("reasoning_tokens", 0)
    )

    return {"text": text, "reasoning_tokens": reasoning_tokens}


async def main() -> None:
    """Run the two-turn conversation demo."""
    first_question = "What is 25 * 48?"
    first_answer = await chat(first_question)

    second_question = "Divide that by 4."
    second_question_context = [
        {"type": "message", "role": "user", "content": first_question},
        {"type": "message", "role": "assistant", "content": first_answer["text"]},
    ]
    second_answer = await chat(second_question, second_question_context)

    print(f"Q: {first_question}")
    print(f"A: {first_answer['text']} ({first_answer['reasoning_tokens']} reasoning tokens)")
    print(f"Q: {second_question}")
    print(f"A: {second_answer['text']} ({second_answer['reasoning_tokens']} reasoning tokens)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
