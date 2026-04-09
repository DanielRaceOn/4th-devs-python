# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
FastAPI application and route handlers — mirrors src/app.ts (Hono).

Routes:
  GET  /api/health   — service health check, includes tracing status
  GET  /api/sessions — list all active in-memory sessions
  POST /api/chat     — send a user message and receive agent response

The ``create_app`` factory accepts dependencies (logger and adapter
resolver) so the entry point can wire them after tracing initialisation.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/app.ts

"""

import uuid
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .agent.run import run_agent
from .core.logger import Logger
from .core.tracing.init import flush, is_tracing_active
from .core.tracing.tracer import set_trace_output, with_trace
from .session import get_session, list_sessions
from .types import AdapterResolver


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ChatBody(BaseModel):
    """Request body for POST /api/chat."""

    session_id: Optional[str] = None
    user_id: Optional[str] = None
    message: str


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(logger: Logger, adapter_resolver: AdapterResolver) -> FastAPI:
    """Construct and configure the FastAPI application.

    Args:
        logger: Root logger instance passed to route handlers.
        adapter_resolver: Callable that resolves a provider to an adapter.

    Returns:
        A configured ``FastAPI`` instance.
    """
    app = FastAPI(title="03_01 Evals")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        """Return service health status."""
        return {
            "ok": True,
            "service": "03_01_evals",
            "tracing": "configured" if is_tracing_active() else "not_configured",
        }

    @app.get("/api/sessions")
    async def sessions() -> list[dict[str, Any]]:
        """List all active sessions."""
        return list_sessions()

    @app.post("/api/chat")
    async def chat(body: ChatBody) -> Any:
        """Send a user message and return the agent response.

        Args:
            body: ChatBody with optional ``session_id`` / ``user_id``
                  and required ``message``.

        Returns:
            JSON with ``session_id``, ``response``, ``turns``, ``usage``,
            and ``history``.
        """
        message = body.message.strip()
        if not message:
            return JSONResponse({"error": "message is required"}, status_code=400)

        session_id = body.session_id or str(uuid.uuid4())
        user_id = body.user_id

        adapter_result = adapter_resolver("openai")
        if not adapter_result.ok:
            error = adapter_result.error
            return JSONResponse(
                {"error": error.message, "code": error.code}, status_code=503
            )
        adapter = adapter_result.value

        session = get_session(session_id)
        request_logger = logger.child(
            {"sessionId": session_id, "userId": user_id or "anonymous"}
        )

        trace_params: dict[str, Any] = {
            "name": "chat-request",
            "session_id": session_id,
            "input": message,
            "metadata": {"provider": "openai", "stream": False},
            "tags": ["chat", "openai", "sync"],
        }
        if user_id:
            trace_params["user_id"] = user_id

        async def _run_and_return() -> dict[str, Any]:
            agent_result = await run_agent(
                adapter=adapter,
                logger=request_logger,
                session=session,
                message=message,
            )
            set_trace_output(agent_result.response)
            return {
                "session_id": session_id,
                "response": agent_result.response,
                "turns": agent_result.turns,
                "usage": agent_result.usage.to_dict(),
                "history": session.messages,
            }

        try:
            result = await with_trace(trace_params, _run_and_return)
            flush()
            return result
        except Exception as exc:
            request_logger.error("chat handler error", {"error": str(exc)})
            return JSONResponse(
                {"error": "Agent execution failed", "detail": str(exc)}, status_code=500
            )

    return app
