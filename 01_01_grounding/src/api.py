# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Responses API client with automatic retry, timeout, and response parsing.
Provides chat(), extract_text(), extract_json(), and extract_sources() helpers
consumed by all pipeline stages.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `src/api.js`

"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import AI_API_KEY, EXTRA_API_HEADERS  # noqa: E402

from .config import api  # noqa: E402

_RETRYABLE_STATUSES = {429, 500, 502, 503}


def _build_request_body(
    *,
    model: str,
    input: Any,
    text_format: dict | None = None,
    tools: list | None = None,
    include: list | None = None,
    reasoning: dict | None = None,
    previous_response_id: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"model": model, "input": input}
    if text_format is not None:
        body["text"] = {"format": text_format}
    if tools is not None:
        body["tools"] = tools
    if include is not None:
        body["include"] = include
    if reasoning is not None:
        body["reasoning"] = reasoning
    if previous_response_id is not None:
        body["previous_response_id"] = previous_response_id
    return body


async def _fetch_with_retry(url: str, **kwargs: Any) -> httpx.Response:
    last_error: Exception = RuntimeError("No attempts made")

    for attempt in range(api["retries"]):
        try:
            async with httpx.AsyncClient(timeout=api["timeout_ms"] / 1000) as client:
                response = await client.post(url, **kwargs)

            if response.is_success:
                return response

            error_text = response.text
            last_error = RuntimeError(
                f"Responses API error ({response.status_code}): {error_text}"
            )

            if response.status_code not in _RETRYABLE_STATUSES:
                raise last_error

            delay = api["retry_delay_ms"] / 1000 * (2 ** attempt)
            logging.warning(
                "  Retry %d/%d after %.0fms (status %d)",
                attempt + 1,
                api["retries"],
                delay * 1000,
                response.status_code,
            )
            await asyncio.sleep(delay)

        except httpx.TimeoutException:
            last_error = RuntimeError(
                f"Request timed out after {api['timeout_ms']}ms"
            )
            if attempt < api["retries"] - 1:
                delay = api["retry_delay_ms"] / 1000 * (2 ** attempt)
                logging.warning(
                    "  Retry %d/%d after %.0fms (%s)",
                    attempt + 1,
                    api["retries"],
                    delay * 1000,
                    last_error,
                )
                await asyncio.sleep(delay)

        except Exception as exc:
            if "Responses API error" in str(exc):
                raise
            last_error = exc
            if attempt < api["retries"] - 1:
                delay = api["retry_delay_ms"] / 1000 * (2 ** attempt)
                logging.warning(
                    "  Retry %d/%d after %.0fms (%s)",
                    attempt + 1,
                    api["retries"],
                    delay * 1000,
                    exc,
                )
                await asyncio.sleep(delay)

    raise last_error


async def chat(
    *,
    model: str,
    input: Any,
    text_format: dict | None = None,
    tools: list | None = None,
    include: list | None = None,
    reasoning: dict | None = None,
    previous_response_id: str | None = None,
) -> dict[str, Any]:
    """Call the Responses API with automatic retry and timeout.

    Args:
        model: Model identifier string (required).
        input: Message or list of messages to send.
        text_format: Optional structured output schema dict.
        tools: Optional list of tool dicts (e.g. web_search).
        include: Optional list of fields to include in the response.
        reasoning: Optional reasoning configuration dict.
        previous_response_id: Optional ID for multi-turn context chaining.

    Returns:
        Parsed JSON response dict from the API.

    Raises:
        ValueError: If ``model`` or ``input`` is missing.
        RuntimeError: If the API returns an error after all retries.
    """
    if not model or not isinstance(model, str):
        raise ValueError("chat: model is required and must be a string")
    if input is None:
        raise ValueError("chat: input is required")

    body = _build_request_body(
        model=model,
        input=input,
        text_format=text_format,
        tools=tools,
        include=include,
        reasoning=reasoning,
        previous_response_id=previous_response_id,
    )

    response = await _fetch_with_retry(
        api["endpoint"],
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}",
            **EXTRA_API_HEADERS,
        },
        content=json.dumps(body),
    )

    data = response.json()
    if data.get("error"):
        raise RuntimeError(data["error"]["message"])

    return data


def extract_text(response: dict[str, Any]) -> str:
    """Extract the output text from an API response.

    Args:
        response: Parsed JSON response from the Responses API.

    Returns:
        The output text string.

    Raises:
        RuntimeError: If no output text is found in the response.
    """
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    messages = [item for item in (response.get("output") or []) if item.get("type") == "message"]
    for msg in messages:
        for part in msg.get("content") or []:
            if part.get("type") == "output_text" and part.get("text"):
                return part["text"]

    types = ", ".join(item.get("type", "") for item in (response.get("output") or [])) or "none"
    raise RuntimeError(f"No output_text in response. Found types: {types}")


def extract_json(response: dict[str, Any], label: str = "response") -> Any:
    """Extract and parse JSON from an API response.

    Args:
        response: Parsed JSON response from the Responses API.
        label: Label used in error messages to identify context.

    Returns:
        Parsed Python object from the JSON output.

    Raises:
        RuntimeError: If JSON parsing fails.
    """
    text = extract_text(response)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        preview = text[:200] + "..." if len(text) > 200 else text
        raise RuntimeError(
            f"Failed to parse JSON for {label}: {exc}\nOutput: {preview}"
        ) from exc


def extract_sources(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract unique web search sources from an API response.

    Collects sources from both ``web_search_call`` action items and
    ``url_citation`` annotations found anywhere in the response tree.

    Args:
        response: Parsed JSON response from the Responses API.

    Returns:
        Deduplicated list of ``{'title': ..., 'url': ...}`` dicts.
    """
    output = response.get("output") or []
    calls = [item for item in output if item.get("type") == "web_search_call"]

    call_sources = [
        source
        for call in calls
        for source in (call.get("action") or {}).get("sources", [])
        if source.get("url")
    ]

    citation_sources: list[dict[str, Any]] = []

    def _collect(node: Any) -> None:
        if not node or not isinstance(node, (dict, list)):
            return
        if isinstance(node, list):
            for item in node:
                _collect(item)
            return
        citation = node.get("url_citation")
        if citation and citation.get("url"):
            citation_sources.append({"title": citation.get("title"), "url": citation["url"]})
        for value in node.values():
            _collect(value)

    _collect(response)

    all_sources = call_sources + citation_sources
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for source in all_sources:
        url = source.get("url", "")
        if url not in seen:
            seen.add(url)
            unique.append(source)
    return unique


# Aliases for backward compatibility
call_responses = chat
parse_json_output = extract_json
get_web_sources = extract_sources
