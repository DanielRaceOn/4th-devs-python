# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
FastAPI HTTP server — mirrors the Hono server in index.ts.

Routes:
  POST /api/chat               — send a message to the agent
  GET  /api/sessions           — list all active sessions
  GET  /api/sessions/{id}/memory — detailed memory state for a session
  POST /api/sessions/{id}/flush  — force-observe all remaining messages

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/index.ts


"""

import uuid
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import (
    AI_API_KEY,
    RESPONSES_ENDPOINT,
    EXTRA_API_HEADERS,
    SERVER_PORT,
    DEFAULT_AGENT_NAME,
    DEFAULT_MEMORY_CONFIG,
)
from .agent.agent import run_agent
from .memory.processor import flush_memory
from .session import get_session, get_or_create_session, list_sessions, build_memory_summary
from .helpers.log import log, log_error
from .helpers.utils import truncate

logger = logging.getLogger(__name__)

# Shared async HTTP client — created at startup, closed at shutdown
_http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the shared HTTP client lifecycle for the FastAPI app."""
    global _http_client
    _http_client = httpx.AsyncClient(timeout=120.0)
    logger.info("HTTP client created")
    yield
    if _http_client:
        await _http_client.aclose()
        logger.info("HTTP client closed")


app = FastAPI(title="02_05 Agent — Context Engineering Demo", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_client() -> httpx.AsyncClient:
    """Return the shared HTTP client, raising if not initialised."""
    if _http_client is None:
        raise RuntimeError("HTTP client is not initialised — server not started properly")
    return _http_client


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/api/chat")
async def post_chat(body: ChatRequest):
    """Send a user message and receive the agent's response.

    Args:
        body: ChatRequest with optional ``session_id`` and required ``message``.

    Returns:
        JSON with ``session_id``, ``response``, ``memory``, and ``usage``.
    """
    session_id = body.session_id or str(uuid.uuid4())
    message = body.message.strip()

    if not message:
        return JSONResponse({"error": "message is required"}, status_code=400)

    session = get_or_create_session(session_id)
    log("session", f'{session_id[:8]} "{truncate(message, 60)}"')

    try:
        result = await run_agent(
            client=_get_client(),
            api_url=RESPONSES_ENDPOINT,
            api_key=AI_API_KEY,
            extra_headers=EXTRA_API_HEADERS,
            session=session,
            user_message=message,
            agent_name=DEFAULT_AGENT_NAME,
        )
        memory_summary = build_memory_summary(session)
        return {
            "session_id": session_id,
            "response": result["response"],
            "memory": {
                "hasObservations": bool(session["memory"].get("active_observations", "")),
                **memory_summary,
            },
            "usage": result["usage"],
        }
    except Exception as err:
        log_error("session", "Agent execution failed:", err)
        return JSONResponse({"error": "Agent execution failed"}, status_code=500)


@app.get("/api/sessions")
async def get_sessions():
    """List all active sessions with summary metrics.

    Returns:
        JSON list of session summary dicts.
    """
    return [
        {
            "id": s["id"],
            "messageCount": len(s["messages"]),
            "observationTokens": s["memory"].get("observation_token_count", 0),
            "generation": s["memory"].get("generation_count", 0),
        }
        for s in list_sessions()
    ]


@app.get("/api/sessions/{session_id}/memory")
async def get_session_memory(session_id: str):
    """Return the full memory state for a session.

    Args:
        session_id: Session identifier.

    Returns:
        JSON with ``session_id``, ``messageCount``, and ``memory``.
    """
    session = get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    return {
        "session_id": session["id"],
        "messageCount": len(session["messages"]),
        "memory": session["memory"],
    }


@app.post("/api/sessions/{session_id}/flush")
async def post_flush(session_id: str):
    """Force-observe all remaining unobserved messages for a session.

    Args:
        session_id: Session identifier.

    Returns:
        JSON with ``session_id`` and updated ``memory`` summary.
    """
    session = get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    log("session", f"{session_id[:8]} Flushing remaining messages to observations")

    try:
        await flush_memory(
            client=_get_client(),
            api_url=RESPONSES_ENDPOINT,
            api_key=AI_API_KEY,
            extra_headers=EXTRA_API_HEADERS,
            session=session,
            config=DEFAULT_MEMORY_CONFIG,
        )
        return {"session_id": session["id"], "memory": build_memory_summary(session)}
    except Exception as err:
        log_error("session", "Flush failed:", err)
        return JSONResponse({"error": "Flush failed"}, status_code=500)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the uvicorn server."""
    import os
    import uvicorn

    port = int(os.environ.get("PORT", SERVER_PORT))
    print()
    print("========================================")
    print("  02_05 Agent — Context Engineering Demo")
    print(f"  http://localhost:{port}")
    print("========================================")
    print()
    uvicorn.run("02_05_agent.src.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
