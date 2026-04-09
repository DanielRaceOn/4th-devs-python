# -*- coding: utf-8 -*-

#   openai.py

"""
### Description:
OpenAI **Responses API** adapter — mirrors src/core/adapters/openai.ts.

Key difference from the ``03_01_observability`` Chat Completions adapter:
  - Uses ``client.responses.create(model, input, instructions, tools)``
  - Extracts text from ``response.output`` items of type ``"message"``
  - Extracts tool calls from items of type ``"function_call"``
    (using ``call_id`` instead of ``id``)
  - Serialises the full output item list to dicts so the agent loop can
    append them to the Responses API input for the next turn

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/core/adapters/openai.ts

"""

from typing import Any, Optional

from ..result import Result, err, ok
from ...types import (
    Adapter,
    CompletionError,
    CompletionParams,
    CompletionResult,
    OutputItem,
    ToolCall,
    Usage,
)

_DEFAULT_MODEL = "gpt-4.1-mini"


def _output_item_to_dict(item: Any) -> OutputItem:
    """Convert a Responses API output item SDK object to a plain dict.

    The Responses API accepts these dicts back as future input items,
    enabling multi-turn conversations.

    Args:
        item: An SDK ``ResponseOutputItem`` object.

    Returns:
        Plain dict suitable for use as a Responses API input item.
    """
    # Try model_dump (Pydantic v2) then dict() then manual reconstruction
    if hasattr(item, "model_dump"):
        return item.model_dump()  # type: ignore[return-value]
    if hasattr(item, "dict"):
        return item.dict()  # type: ignore[return-value]

    # Manual fallback for function_call items
    if getattr(item, "type", None) == "function_call":
        return {
            "type": "function_call",
            "id": getattr(item, "id", ""),
            "call_id": getattr(item, "call_id", ""),
            "name": getattr(item, "name", ""),
            "arguments": getattr(item, "arguments", ""),
        }

    # Fallback: convert whatever attributes are present
    return {k: v for k, v in vars(item).items() if not k.startswith("_")}


def _map_error(exc: Exception) -> CompletionError:
    """Map an OpenAI SDK exception to a typed CompletionError.

    Args:
        exc: Exception raised by the OpenAI SDK.

    Returns:
        A ``CompletionError`` with an appropriate code.
    """
    try:
        import openai as _openai  # type: ignore[import]
    except ImportError:
        return CompletionError(code="UNKNOWN_ERROR", message=str(exc), provider="openai")

    if isinstance(exc, _openai.AuthenticationError):
        return CompletionError(code="AUTHENTICATION_ERROR", message=str(exc), provider="openai", status=401)
    if isinstance(exc, _openai.RateLimitError):
        return CompletionError(code="RATE_LIMITED", message=str(exc), provider="openai", status=429)
    if isinstance(exc, _openai.BadRequestError):
        return CompletionError(code="BAD_REQUEST", message=str(exc), provider="openai", status=400)
    if isinstance(exc, _openai.APIConnectionError):
        return CompletionError(code="CONNECTION_ERROR", message=str(exc), provider="openai")
    if isinstance(exc, _openai.APITimeoutError):
        return CompletionError(code="TIMEOUT", message=str(exc), provider="openai")
    if isinstance(exc, _openai.InternalServerError):
        return CompletionError(code="INTERNAL_SERVER_ERROR", message=str(exc), provider="openai", status=500)

    return CompletionError(code="UNKNOWN_ERROR", message=str(exc), provider="openai")


class _OpenAIResponsesAdapter(Adapter):
    """OpenAI Responses API adapter."""

    def __init__(self, config: dict[str, Any]) -> None:
        import openai as _openai  # type: ignore[import]

        self._model: str = config.get("default_model", _DEFAULT_MODEL)
        self._client = _openai.AsyncOpenAI(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url") or None,
            default_headers=config.get("default_headers") or {},
        )

    async def complete(
        self, params: CompletionParams
    ) -> "Result[CompletionResult, CompletionError]":
        """Issue a Responses API request and return a typed Result.

        Args:
            params: Completion parameters including input items, model, tools.

        Returns:
            ``ok(CompletionResult)`` on success, ``err(CompletionError)`` on failure.
        """
        model = params.model or self._model

        kwargs: dict[str, Any] = {
            "model": model,
            "input": params.input,
        }
        if params.instructions:
            kwargs["instructions"] = params.instructions
        if params.tools:
            kwargs["tools"] = params.tools

        try:
            response = await self._client.responses.create(**kwargs)
        except Exception as exc:
            return err(_map_error(exc))

        # Extract text and tool calls from the output items list
        text = ""
        tool_calls: list[ToolCall] = []
        output_dicts: list[OutputItem] = []

        for item in response.output:
            item_type = getattr(item, "type", None)

            # Serialise every output item so it can be replayed as input
            output_dicts.append(_output_item_to_dict(item))

            if item_type == "message":
                # Text response: concatenate all text content parts
                for part in getattr(item, "content", []):
                    part_text = getattr(part, "text", None)
                    if part_text:
                        text += part_text

            elif item_type == "function_call":
                tool_calls.append(
                    ToolCall(
                        call_id=getattr(item, "call_id", ""),
                        name=getattr(item, "name", ""),
                        arguments=getattr(item, "arguments", "{}"),
                    )
                )

        usage: Optional[Usage] = None
        if response.usage:
            usage = Usage(
                input=getattr(response.usage, "input_tokens", None),
                output=getattr(response.usage, "output_tokens", None),
                total=getattr(response.usage, "total_tokens", None),
            )

        return ok(
            CompletionResult(
                text=text,
                tool_calls=tool_calls,
                output=output_dicts,
                usage=usage,
            )
        )


def openai_adapter(config: dict[str, Any]) -> Adapter:
    """Construct an OpenAI Responses API adapter.

    Args:
        config: Dict with keys:
            - ``api_key``         (str)
            - ``base_url``        (str, optional)
            - ``default_headers`` (dict, optional)
            - ``default_model``   (str, optional)

    Returns:
        A configured ``Adapter`` instance.
    """
    return _OpenAIResponsesAdapter(config)
