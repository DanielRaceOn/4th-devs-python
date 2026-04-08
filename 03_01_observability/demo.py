# -*- coding: utf-8 -*-

#   demo.py

"""
### Description:
Demo script — sends a scripted 3-message conversation to the running
03_01_observability server, mirrors demo.ts.

The same session ID is reused across all messages so the server can
observe the full conversation in Langfuse.

Usage:
    # Start the server first:
    .venv/Scripts/python 03_01_observability/app.py

    # Then in another terminal:
    .venv/Scripts/python 03_01_observability/demo.py

---

@Author:        Claude Sonnet 4.6
@Created on:    08.04.2026
@Based on:      demo.ts

"""

import asyncio
import json
import os
import sys
import time

import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:3010")
SESSION = f"demo-{int(time.time())}"

MESSAGES = [
    "Hey, can you tell me what time it is in UTC?",
    "Now sum these numbers: 3, 11, 21, 34",
    "Great, briefly summarize what you just did.",
]

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------


def BLUE(s: str) -> str:    return f"\x1b[34m{s}\x1b[0m"   # noqa: E704
def GREEN(s: str) -> str:   return f"\x1b[32m{s}\x1b[0m"   # noqa: E704
def YELLOW(s: str) -> str:  return f"\x1b[33m{s}\x1b[0m"   # noqa: E704
def DIM(s: str) -> str:     return f"\x1b[2m{s}\x1b[0m"    # noqa: E704
def RED(s: str) -> str:     return f"\x1b[31m{s}\x1b[0m"   # noqa: E704


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def ensure_server(client: httpx.AsyncClient) -> None:
    """Verify the observability server is reachable before running.

    Args:
        client: Shared async HTTP client.

    Raises:
        SystemExit: If the server is not reachable.
    """
    try:
        resp = await client.get(f"{BASE}/api/health")
        data = resp.json()
        tracing = data.get("tracing", "unknown")
        print(f"  Server OK — tracing: {tracing}")
    except Exception:
        print(f"\n{RED('Error: Server is not running at ' + BASE)}")
        print("  Start it first in another terminal:")
        print("  .venv/Scripts/python 03_01_observability/app.py\n")
        sys.exit(1)


async def send(
    client: httpx.AsyncClient, label: str, message: str
) -> None:
    """Send one message to the agent and print the response.

    Args:
        client: Shared async HTTP client.
        label: Display label, e.g. ``"1/3"``.
        message: User message text.
    """
    print()
    print(BLUE(f"--- Message {label} " + "-" * 35))
    print(YELLOW(f"> {message}"))
    print()

    resp = await client.post(
        f"{BASE}/api/chat",
        json={"session_id": SESSION, "message": message},
        timeout=120.0,
    )

    if resp.status_code != 200:
        print(f"{RED('Error')} HTTP {resp.status_code}: {resp.text}")
        return

    data = resp.json()
    response_text = data.get("response") or "(no response)"
    print(GREEN(f"< {response_text}"))
    print()

    usage = data.get("usage") or {}
    turns = data.get("turns", "?")
    print(
        DIM(
            f"   turns={turns}  "
            f"input_tokens={usage.get('input', '?')}  "
            f"output_tokens={usage.get('output', '?')}  "
            f"total_tokens={usage.get('total', '?')}"
        )
    )

    # 500 ms delay between messages
    await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the full scripted demo conversation."""
    print()
    print("=" * 42)
    print("  03_01 Observability — Demo")
    print(f"  session: {SESSION}")
    print(f"  server:  {BASE}")
    print("=" * 42)

    async with httpx.AsyncClient(timeout=120.0) as client:
        await ensure_server(client)

        total = len(MESSAGES)
        for i, msg in enumerate(MESSAGES):
            await send(client, f"{i + 1}/{total}", msg)

        # Print final history
        print()
        print(BLUE("--- Final session history " + "-" * 17))
        hist_resp = await client.post(
            f"{BASE}/api/chat",
            json={"session_id": SESSION, "message": "Thank you!"},
            timeout=120.0,
        )
        if hist_resp.status_code == 200:
            history = hist_resp.json().get("history") or []
            print(DIM(f"   {len(history)} messages in history"))
            for m in history:
                role = m.get("role", "?")
                content = str(m.get("content") or "")[:80]
                print(DIM(f"   [{role}] {content}"))

    print()


if __name__ == "__main__":
    asyncio.run(main())
