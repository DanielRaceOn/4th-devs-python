# -*- coding: utf-8 -*-

#   elicitation.py

"""
### Description:
Elicitation handler — auto-accepts MCP forms with inferred defaults.
Elicitation is a protocol feature where the server asks the client for
structured user input. In this demo we auto-accept every form by inferring
defaults from the JSON Schema — no real user interaction needed.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/elicitation.js`

"""

from typing import Any, Callable, Optional

from .log import client_log


def _infer_default(prop: dict) -> Any:
    """Pick a reasonable default for a single JSON Schema property.

    Priority: explicit default → boolean true → first enum value.
    """
    if "default" in prop:
        return prop["default"]
    if prop.get("type") == "boolean":
        return True
    enum = prop.get("enum")
    if enum:
        return enum[0]
    return None


def _auto_fill_defaults(schema: dict) -> dict:
    """Walk schema properties and build a {key: value} map of inferred defaults."""
    properties = (schema or {}).get("properties", {})
    result = {}
    for key, prop in properties.items():
        value = _infer_default(prop)
        if value is not None:
            result[key] = value
    return result


def create_elicitation_handler(on_elicitation: Optional[Callable] = None):
    """Return an async elicitation callback for the MCP client.

    Args:
        on_elicitation: Optional custom handler. If provided, it is called
            instead of auto-accepting. Must be an async callable.

    Returns:
        Async callable that accepts an elicitation request and returns a dict
        with ``action`` and optionally ``content``.
    """
    async def handler(request: Any) -> dict:
        params = request.params if hasattr(request, "params") else request
        mode = getattr(params, "mode", "form")

        client_log.elicitation_request(mode)

        # Only "form" mode is supported by the spec right now
        if mode != "form":
            return {"action": "decline"}

        # Let the caller override with real UI if needed
        if callable(on_elicitation):
            return await on_elicitation(params)

        # Demo mode: auto-fill the form from schema defaults
        schema = getattr(params, "requestedSchema", {})
        if hasattr(schema, "__dict__"):
            schema = schema.__dict__
        content = _auto_fill_defaults(schema)
        client_log.auto_accepted_elicitation(content)

        return {"action": "accept", "content": content}

    return handler
