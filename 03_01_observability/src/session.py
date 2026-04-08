# -*- coding: utf-8 -*-

#   session.py

"""
### Description:
In-memory session store — mirrors src/session.ts.

Sessions are keyed by their string ID.  ``get_session`` creates a new
session if none exists for the given ID.  ``list_sessions`` returns a
summary list suitable for the ``/api/sessions`` endpoint.

---

@Author:        Claude Sonnet 4.6
@Created on:    08.04.2026
@Based on:      src/session.ts

"""

from typing import Any

from .types import Session

# Module-level in-memory store
_sessions: dict[str, Session] = {}


def get_session(session_id: str) -> Session:
    """Return the existing session or create and store a new one.

    Args:
        session_id: Unique session identifier string.

    Returns:
        The existing or newly created ``Session``.
    """
    existing = _sessions.get(session_id)
    if existing is not None:
        return existing
    created = Session(id=session_id)
    _sessions[session_id] = created
    return created


def list_sessions() -> list[dict[str, Any]]:
    """Return a summary list of all active sessions.

    Returns:
        List of dicts with ``id`` and ``messageCount`` keys.
    """
    return [
        {"id": s.id, "messageCount": len(s.messages)}
        for s in _sessions.values()
    ]
