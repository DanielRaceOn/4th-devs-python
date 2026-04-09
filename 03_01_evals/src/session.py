# -*- coding: utf-8 -*-

#   session.py

"""
### Description:
In-memory session store — mirrors src/session.ts.

Provides ``get_session`` (create-or-return) and ``list_sessions``
(summary listing) backed by a plain Python dict.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/session.ts

"""

from .types import Session

_sessions: dict[str, Session] = {}


def get_session(session_id: str) -> Session:
    """Return an existing session or create a new one.

    Args:
        session_id: Unique session identifier.

    Returns:
        The ``Session`` object (created if it did not exist).
    """
    if session_id not in _sessions:
        _sessions[session_id] = Session(id=session_id)
    return _sessions[session_id]


def list_sessions() -> list[dict[str, object]]:
    """Return a summary list of all active sessions.

    Returns:
        List of dicts with ``id`` and ``messageCount`` keys.
    """
    return [
        {"id": s.id, "messageCount": len(s.messages)}
        for s in _sessions.values()
    ]
