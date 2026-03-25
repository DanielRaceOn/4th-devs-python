# -*- coding: utf-8 -*-

#   demo.py

"""
### Description:
Demo script that sends a scripted sequence of messages to the running agent
server, printing responses and memory metrics — mirrors demo.ts.

Usage:
    # Start the server first:
    .venv/Scripts/python -m uvicorn 02_05_agent.src.app:app --port 3001

    # Then in another terminal:
    .venv/Scripts/python 02_05_agent/demo.py

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      demo.ts


"""

import asyncio
import json
import os
import sys
import time

import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:3001")
SESSION = f"demo-{int(time.time())}"

# ANSI colour helpers
def BLUE(s: str) -> str:   return f"\x1b[34m{s}\x1b[0m"  # noqa: E704
def GREEN(s: str) -> str:  return f"\x1b[32m{s}\x1b[0m"  # noqa: E704
def YELLOW(s: str) -> str: return f"\x1b[33m{s}\x1b[0m"  # noqa: E704
def DIM(s: str) -> str:    return f"\x1b[2m{s}\x1b[0m"   # noqa: E704
def CYAN(s: str) -> str:   return f"\x1b[36m{s}\x1b[0m"  # noqa: E704

MESSAGES = [
    # Phase 1: Building identity
    "Hi! My name is Adam. I'm a developer from Poland.",
    "I run a company called easy_ and we build AI-powered automation tools.",
    "My favorite programming language is TypeScript but I also enjoy Rust for performance-critical stuff.",

    # Phase 2: Active work context -- should trigger first observation
    "I'm currently working on a presentation about agentic context engineering. The deadline is next Friday.",
    "The key topics I want to cover are: observer pattern, reflector pattern, and token estimation heuristics.",

    # Phase 3: Personal preferences + tool use
    "Can you write a file notes/adam-profile.md with a summary of what you know about me?",
    "I prefer dark mode in all my apps and I drink flat white coffee. My dog's name is Alexa.",

    # Phase 4: More context to push observations past reflection threshold
    "For the presentation, I'm using a project called 01_05_agent as the reference implementation.",
    "The audience will be experienced developers who already know TypeScript and Node.js.",
    "I also want to demonstrate how token estimation uses chars/4 heuristic with API calibration.",

    # Phase 5: State changes + memory recall
    "Actually, I changed my mind about Rust. I'm more into Go these days for backend work.",
    "Quick check — what do you remember about my presentation? What topics am I covering?",

    # Phase 6: Final comprehensive memory test
    "Summarize everything you know about me in a few bullet points.",
]


async def send(client: httpx.AsyncClient, label: str, message: str) -> None:
    """Send one message to the agent and print the response + memory metrics.

    Args:
        client: Shared async HTTP client.
        label: Display label (e.g. "1/13").
        message: User message text.
    """
    print()
    print(BLUE(f"--- Message {label} ---------------------------------------"))
    print(YELLOW(f"> {message}"))
    print()

    resp = await client.post(
        f"{BASE}/api/chat",
        json={"session_id": SESSION, "message": message},
    )
    data = resp.json()

    response_text = data.get("response") or "no response"
    print(GREEN(f"< {response_text}"))
    print()

    memory = data.get("memory") or {}
    usage  = data.get("usage")  or {}

    gen       = memory.get("generation", 0)
    sealed    = memory.get("sealed_messages", 0)
    active    = memory.get("active_messages", 0)
    obs_tok   = memory.get("observation_tokens", 0)
    has_obs   = memory.get("hasObservations", False)

    gen_label  = CYAN(f" ★ gen {gen} (reflector ran)") if gen > 0 else ""
    seal_label = YELLOW(f" [{sealed} sealed, {active} active]") if sealed > 0 else ""

    cal_ratio = (usage.get("calibration") or {}).get("ratio")
    cal_str   = f"{cal_ratio:.2f}" if cal_ratio is not None else "n/a"

    print(
        DIM(f"   memory: observations={has_obs} tokens={obs_tok} generation={gen}")
        + gen_label + seal_label
    )
    print(
        DIM(
            f"   usage:  estimated={usage.get('total_estimated_tokens', '?')} "
            f"actual={usage.get('total_actual_tokens', '?')} "
            f"calibration={cal_str}"
        )
    )

    await asyncio.sleep(1)


async def ensure_server(client: httpx.AsyncClient) -> None:
    """Verify the agent server is reachable before running the demo.

    Args:
        client: Shared async HTTP client.

    Raises:
        SystemExit: If the server is not reachable.
    """
    try:
        await client.get(f"{BASE}/api/sessions")
    except Exception:
        print(f"\n\x1b[31mError: Agent server is not running at {BASE}\x1b[0m")
        print("       Start it first in another terminal:")
        print("       .venv/Scripts/python -m uvicorn 02_05_agent.src.app:app --port 3001\n")
        sys.exit(1)


async def main() -> None:
    """Run the full scripted demo conversation."""
    print()
    print("========================================")
    print("  02_05 Agent — Continuity Demo")
    print(f"  session: {SESSION}")
    print("========================================")

    async with httpx.AsyncClient(timeout=120.0) as client:
        await ensure_server(client)

        total = len(MESSAGES)
        for i, msg in enumerate(MESSAGES):
            await send(client, f"{i + 1}/{total}", msg)

        # Flush remaining messages to observations
        print()
        print(BLUE("--- Flushing remaining messages to observations -----------"))
        flush_resp = await client.post(f"{BASE}/api/sessions/{SESSION}/flush")
        flush_data = flush_resp.json()
        fm = flush_data.get("memory") or {}
        print(
            DIM(
                f"   sealed={fm.get('sealed_messages', '?')} "
                f"active={fm.get('active_messages', '?')} "
                f"generation={fm.get('generation', '?')} "
                f"tokens={fm.get('observation_tokens', '?')}"
            )
        )

        # Final memory state
        print()
        print(BLUE("--- Final Memory State ------------------------------------"))
        mem_resp = await client.get(f"{BASE}/api/sessions/{SESSION}/memory")
        print(json.dumps(mem_resp.json(), indent=2))
        print()


if __name__ == "__main__":
    asyncio.run(main())
