# -*- coding: utf-8 -*-

#   server.py

"""
### Description:
In-memory MCP server with mock tools (weather, time).
Unlike mcp_core which uses stdio transport, this server runs in the
same process and connects via in-memory transport.
The tools are intentionally simple — the point of this example is
the unified agent loop, not the tool implementations.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/mcp/server.js`

"""

import json
import random
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

mcp_server = FastMCP("demo-mcp-server")


@mcp_server.tool()
def get_weather(city: str) -> str:
    """Get current weather for a city.

    Args:
        city: City name.

    Returns:
        JSON string with city, condition, and temperature.
    """
    conditions = ["sunny", "cloudy", "rainy", "snowy"]
    condition = random.choice(conditions)
    temp = random.randint(-5, 30)
    return json.dumps({"city": city, "condition": condition, "temperature": f"{temp}°C"})


@mcp_server.tool()
def get_time(timezone_str: str) -> str:
    """Get current time in a specified timezone.

    Args:
        timezone_str: Timezone string (e.g. ``"UTC"``, ``"America/New_York"``).

    Returns:
        JSON string with timezone and time, or error if invalid.
    """
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(timezone_str)
        time_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        return json.dumps({"timezone": timezone_str, "time": time_str})
    except Exception as e:
        return json.dumps({"error": f"Invalid timezone: {timezone_str}"})
