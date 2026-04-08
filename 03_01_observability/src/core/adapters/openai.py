# -*- coding: utf-8 -*-

#   openai.py

"""
### Description:
OpenAI Chat Completions adapter — mirrors src/core/adapters/openai.ts.

Wraps the ``openai`` Python SDK to:
  - Build the message list (prepending a system message when ``instructions``
    is present)
  - Issue ``chat.completions.create`` with tools if supplied
  - Map OpenAI SDK exceptions to typed ``CompletionError`` codes
  - Return ``ok(CompletionResult)`` or ``err(CompletionError)``

---

@Author:        Claude Sonnet 4.6
@Created on:    08.04.2026
@Based on:      src/core/adapters/openai.ts

"""

from typing import Any, Optional

from ..result import Result, err, ok
from ...types import (
    Adapter,
    CompletionError,
    CompletionParams,
    CompletionResult,
    ToolCall,
    Usage,
)

_DEFAULT_MODEL = "gpt-4o-mini"


def _build_messages(params: CompletionParams) -> list[dict[str, Any]]:
    """Prepend a system message when ``instructions`` is present.

    Args:
        params: Completion parameters.

    Returns:
        Message list ready to pass to the OpenAI API.
    """
    messages: list[dict[str, Any]] = list(params.input)
    if params.instructions:
        messages = [{"role": "system", "content": params.instructions}] + messages
    return messages


def _map_error(exc: Exception) -> CompletionError:
    """Map an OpenAI SDK exception to a typed CompletionError.

    Args:
        exc: Exception raised by the OpenAI SDK.

    Returns:
        A ``CompletionError`` with an appropriate code.
    """
    # Import here to avoid mandatory dependency at module load time
    try:
        import openai as _openai  # type: ignore[import]
    except ImportError:
        return CompletionError(
            code="UNKNOWN_ERROR",
            message=str(exc),
            provider="openai",
        )

    if isinstance(exc, _openai.AuthenticationError):
        return CompletionError(
            code="AUTHENTICATION_ERROR",
            message=str(exc),
            provider="openai",
            status=401,
        )
    if isinstance(exc, _openai.RateLimitError):
        return CompletionError(
            code="RATE_LIMITED",
            message=str(exc),
            provider="openai",
            status=429,
        )
    if isinstance(exc, _openai.BadRequestError):
        return CompletionError(
            code="BAD_REQUEST",
            message=str(exc),
            provider="openai",
            status=400,
        )
    if isinstance(exc, _openai.APIConnectionError):
        return CompletionError(
            code="CONNECTION_ERROR",
            message=str(exc),
            provider="openai",
        )
    if isinstance(exc, _openai.APITimeoutError):
        return CompletionError(
            code="TIMEOUT",
            message=str(exc),
            provider="openai",
        )
    if isinstance(exc, _openai.InternalServerError):
        return CompletionError(
            code="INTERNAL_SERVER_ERROR",
            message=str(exc),
            provider="openai",
            status=500,
        )
    return CompletionError(
        code="UNKNOWN_ERROR",
        message=str(exc),
        provider="openai",
    )


class _OpenAIAdapter(Adapter):
    """OpenAI Chat Completions adapter."""

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
        """Issue a Chat Completions request and return a typed Result.

        Args:
            params: Completion parameters including messages, model, tools.

        Returns:
            ``ok(CompletionResult)`` on success, ``err(CompletionError)`` on
            failure.
        """
        model = params.model or self._model
        messages = _build_messages(params)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if params.tools:
            kwargs["tools"] = params.tools
        if params.tool_choice is not None:
            kwargs["tool_choice"] = params.tool_choice

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            return err(_map_error(exc))

        choice = response.choices[0] if response.choices else None
        if choice is None:
            return err(
                CompletionError(
                    code="UNKNOWN_ERROR",
                    message="No choices returned by the API",
                    provider="openai",
                )
            )

        msg = choice.message
        text: str = msg.content or ""

        tool_calls: list[ToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )

        usage: Optional[Usage] = None
        if response.usage:
            usage = Usage(
                input=response.usage.prompt_tokens,
                output=response.usage.completion_tokens,
                total=response.usage.total_tokens,
            )

        return ok(CompletionResult(text=text, tool_calls=tool_calls, usage=usage))


def openai_adapter(config: dict[str, Any]) -> Adapter:
    """Construct an OpenAI Chat Completions adapter.

    Args:
        config: Dict with keys:
            - ``api_key``       (str)
            - ``base_url``      (str, optional)
            - ``default_headers`` (dict, optional)
            - ``default_model`` (str, optional)

    Returns:
        A configured ``Adapter`` instance.
    """
    return _OpenAIAdapter(config)
