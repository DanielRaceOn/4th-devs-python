# -*- coding: utf-8 -*-

#   demo.py

"""
### Description:
Demo script — sends three messages to the running 03_01_evals server
and prints responses.  Mirrors demo.ts.

Requires the server to be running:
    .venv/Scripts/python 03_01_evals/app.py

Usage:
    .venv/Scripts/python 03_01_evals/demo.py

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      demo.ts

"""

import asyncio
import os
import sys
import time

import httpx

PORT = os.environ.get("PORT", "3010")
BASE_URL = os.environ.get("BASE_URL", f"http://localhost:{PORT}")
SESSION_ID = f"obs-demo-{int(time.time() * 1000)}"

MESSAGES = [
    "Hey, can you tell me what time it is in UTC?",
    "Now sum these numbers: 3, 11, 21, 34",
    "Great, briefly summarize what you just did.",
]


async def ensure_server_running(client: httpx.AsyncClient) -> None:
    """Check the server health endpoint and exit if unreachable.

    Args:
        client: Shared httpx async client.
    """
    try:
        await client.get(f"{BASE_URL}/api/health")
    except Exception:
        print(f"\n  ✖ Server not running at {BASE_URL}")
        print("    Start it first in a separate terminal:")
        print("")
        print("    .venv/Scripts/python 03_01_evals/app.py")
        print("")
        sys.exit(1)


async def main() -> None:
    """Run the demo conversation."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        await ensure_server_running(client)
        print(f"Demo session: {SESSION_ID}")

        for message in MESSAGES:
            response = await client.post(
                f"{BASE_URL}/api/chat",
                json={
                    "session_id": SESSION_ID,
                    "user_id": "demo-user",
                    "message": message,
                },
            )
            data = response.json()

            print("\n---")
            print(f"User:      {message}")
            print(f"Assistant: {data.get('response') or data.get('error')}")
            print(f"Turns:     {data.get('turns', 'n/a')}")
            print(f"Usage:     {data.get('usage', {})}")

            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
