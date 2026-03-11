# -*- coding: utf-8 -*-

#   sampling.py

"""
### Description:
Sampling handler — bridges MCP sampling requests to the AI provider.
Sampling is a protocol feature where the server asks the client to generate
an LLM completion on its behalf. The client returns the model's response.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/sampling.js`

"""

import asyncio
from typing import Any

from mcp.types import CreateMessageResult, TextContent

from .ai import completion
from .log import client_log


def create_sampling_handler(model: str):
    """Return an async sampling callback for the MCP client.

    The callback is called when the server sends a sampling/createMessage
    request. It calls the AI provider and returns the completion.

    Args:
        model: Model identifier to pass to the AI provider.

    Returns:
        Async callable that accepts a sampling request and returns a result.
    """
    async def handler(request: Any) -> CreateMessageResult:
        params = request.params if hasattr(request, "params") else request
        messages = getattr(params, "messages", [])
        max_tokens = getattr(params, "maxTokens", None)

        client_log.sampling_request(messages, max_tokens)

        # Convert MCP message format → Responses API input format
        input_messages = []
        for msg in messages:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", None)
            if content is None:
                continue
            if hasattr(content, "text"):
                text = content.text
            else:
                text = str(content)
            input_messages.append({"role": role, "content": text})

        try:
            text = await completion(
                model=model,
                input=input_messages,
                max_output_tokens=max_tokens or 500,
            )
            client_log.sampling_response(text)

            return CreateMessageResult(
                role="assistant",
                content=TextContent(type="text", text=text),
                model=model,
            )
        except Exception as error:
            client_log.sampling_error(error)
            raise

    return handler
