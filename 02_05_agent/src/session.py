# -*- coding: utf-8 -*-

#   session.py

"""
### Description:
In-memory session store.  Sessions are keyed by a string session ID and hold
the message history plus the ``memory`` state dict used by the observer /
reflector subsystem.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/session.ts


"""

from .types import fresh_memory

# Global in-process session registry  {session_id -> session dict}
_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict | None:
    """Return an existing session or ``None``.

    Args:
        session_id: Unique session identifier.

    Returns:
        Session dict or ``None`` if not found.
    """
    return _sessions.get(session_id)


def get_or_create_session(session_id: str) -> dict:
    """Return an existing session, creating a fresh one if needed.

    Args:
        session_id: Unique session identifier.

    Returns:
        Session dict with ``id``, ``messages``, and ``memory``.
    """
    existing = _sessions.get(session_id)
    if existing:
        return existing

    session: dict = {
        "id": session_id,
        "messages": [],
        "memory": fresh_memory(),
    }
    _sessions[session_id] = session
    return session


def list_sessions() -> list[dict]:
    """Return all active sessions.

    Returns:
        List of all session dicts.
    """
    return list(_sessions.values())


def build_memory_summary(session: dict) -> dict:
    """Build a compact memory-state summary for the API response.

    Args:
        session: Session dict containing ``messages`` and ``memory``.

    Returns:
        Dict with observation and message count metrics.
    """
    memory = session["memory"]
    return {
        "observation_tokens": memory.get("observation_token_count", 0),
        "generation": memory.get("generation_count", 0),
        "total_messages": len(session["messages"]),
        "sealed_messages": memory.get("last_observed_index", 0),
        "active_messages": len(session["messages"]) - memory.get("last_observed_index", 0),
    }
