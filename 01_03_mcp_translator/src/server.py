# -*- coding: utf-8 -*-

#   server.py

"""
### Description:
HTTP server — exposes /api/chat and /api/translate endpoints.
Both routes delegate to the same agent loop. The server is a thin
HTTP shell around the MCP-backed translation agent.
Uses Python's built-in http.server for a zero-dependency HTTP layer.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/server.js`

"""

import asyncio
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Callable

from mcp import ClientSession

from .agent import run
from .helpers.logger import log


def _get_public_base_url(host: str, port: int) -> str:
    public_host = "localhost" if host in ("0.0.0.0", "::") else host
    return f"http://{public_host}:{port}"


def start_http_server(
    config,
    get_mcp_context: Callable,
) -> HTTPServer:
    """Create and start the HTTP server in a background thread.

    Args:
        config: Server config with ``host`` and ``port`` attributes.
        get_mcp_context: Callable returning ``{"mcp_client": ..., "mcp_tools": ...}``.

    Returns:
        The running ``HTTPServer`` instance.
    """
    loop = asyncio.get_event_loop()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # Silence default access log; we use our own logger

        def _send_json(self, status: int, data: dict) -> None:
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def _read_body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            return json.loads(raw) if raw else {}

        def do_POST(self):
            context = get_mcp_context()
            mcp_client: ClientSession = context.get("mcp_client")
            mcp_tools = context.get("mcp_tools", [])

            if not mcp_client:
                return self._send_json(503, {"error": "MCP client not connected"})

            body = self._read_body()

            if self.path == "/api/chat":
                message = body.get("message")
                if not message:
                    return self._send_json(400, {"error": "Message is required"})

                try:
                    result = asyncio.run_coroutine_threadsafe(
                        run(message, mcp_client=mcp_client, mcp_tools=mcp_tools),
                        loop,
                    ).result()
                    return self._send_json(200, result)
                except Exception as error:
                    log.error("Request error", str(error))
                    return self._send_json(500, {"error": str(error)})

            if self.path == "/api/translate":
                text = body.get("text")
                if not text:
                    return self._send_json(400, {"error": "Text is required"})

                query = (
                    "Translate the following text to English. "
                    f"Preserve tone, formatting, and nuances:\n\n{text}"
                )
                try:
                    result = asyncio.run_coroutine_threadsafe(
                        run(query, mcp_client=mcp_client, mcp_tools=mcp_tools),
                        loop,
                    ).result()
                    return self._send_json(200, {"translation": result["response"]})
                except Exception as error:
                    log.error("Request error", str(error))
                    return self._send_json(500, {"error": str(error)})

            self._send_json(404, {"error": "Not found"})

    server = HTTPServer((config.host, config.port), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = _get_public_base_url(config.host, config.port)
    log.ready(f"Server listening on {base_url}")
    log.info("Endpoints:")
    log.endpoint("POST", "/api/chat", "Chat with agent")
    log.endpoint("POST", "/api/translate", "Translate text")
    log.info("Example curl:")
    log.info(
        f'  curl -X POST "{base_url}/api/translate" '
        '-H "Content-Type: application/json" '
        "-d '{\"text\":\"To jest przykladowy tekst po polsku.\"}'"
    )

    return server
