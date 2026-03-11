# -*- coding: utf-8 -*-

#   resources.py

"""
### Description:
MCP resource definitions for the demo server.
Resources are read-only data the server exposes to clients — can be
static (fixed content) or dynamic (generated per request).

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/resources.js`

"""

import json
import time
from datetime import datetime, timezone


# Track server uptime and request count for the dynamic stats resource
_start_time: float = time.time()
_request_count: int = 0


def get_project_config() -> dict:
    """Static resource — always returns the same project metadata."""
    return {
        "uri": "config://project",
        "mimeType": "application/json",
        "text": json.dumps(
            {
                "name": "mcp-core-demo",
                "version": "1.0.0",
                "features": ["tools", "resources", "prompts", "elicitation", "sampling"],
            },
            indent=2,
        ),
    }


def get_runtime_stats() -> dict:
    """Dynamic resource — content changes on every read."""
    global _request_count
    _request_count += 1

    return {
        "uri": "data://stats",
        "mimeType": "application/json",
        "text": json.dumps(
            {
                "uptime_seconds": int(time.time() - _start_time),
                "request_count": _request_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
    }
