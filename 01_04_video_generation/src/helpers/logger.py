# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Simple colored terminal logger with timestamp support.

---

@Author:        Claude Sonnet 4.6
@Created on:    12.03.2026
@Based on:      helpers/logger.js

"""

from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BRIGHT = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"


def timestamp() -> str:
    """Get current time as HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


class Logger:
    """Terminal logger with colored output and timestamps."""

    @staticmethod
    def info(msg: str) -> None:
        """Log informational message."""
        print(f"{Colors.DIM}[{timestamp()}]{Colors.RESET} {msg}")

    @staticmethod
    def success(msg: str) -> None:
        """Log success message with green checkmark."""
        print(f"{Colors.DIM}[{timestamp()}]{Colors.RESET} {Colors.GREEN}✓{Colors.RESET} {msg}")

    @staticmethod
    def error(title: str, msg: str = "") -> None:
        """Log error message with red X."""
        print(
            f"{Colors.DIM}[{timestamp()}]{Colors.RESET} {Colors.RED}✗ {title}{Colors.RESET} {msg}"
        )

    @staticmethod
    def warn(msg: str) -> None:
        """Log warning message with yellow triangle."""
        print(f"{Colors.DIM}[{timestamp()}]{Colors.RESET} {Colors.YELLOW}⚠{Colors.RESET} {msg}")

    @staticmethod
    def start(msg: str) -> None:
        """Log start message with cyan arrow."""
        print(f"{Colors.DIM}[{timestamp()}]{Colors.RESET} {Colors.CYAN}→{Colors.RESET} {msg}")

    @staticmethod
    def box(text: str) -> None:
        """Print text in a box with borders."""
        lines = text.split("\n")
        width = max(len(line) for line in lines) + 4
        print(f"\n{Colors.CYAN}{'─' * width}{Colors.RESET}")
        for line in lines:
            padded = line.ljust(width - 3)
            print(f"{Colors.CYAN}│{Colors.RESET} {Colors.BRIGHT}{padded}{Colors.RESET}{Colors.CYAN}│{Colors.RESET}")
        print(f"{Colors.CYAN}{'─' * width}{Colors.RESET}\n")

    @staticmethod
    def heading(title: str, description: str = "") -> None:
        """Log heading with title and optional description."""
        print(f"\n{Colors.BRIGHT}═══ {title} ═══{Colors.RESET}")
        if description:
            print(f"{Colors.DIM}{description}{Colors.RESET}")

    @staticmethod
    def detail(label: str, data=None) -> None:
        """Log detailed information with label."""
        print(f"\n{Colors.BRIGHT}{Colors.CYAN}▶ {label}{Colors.RESET}")
        if data is None:
            return
        if isinstance(data, str):
            lines = [data]
        elif isinstance(data, list):
            lines = data
        else:
            import json
            lines = json.dumps(data, indent=2).split("\n")
        for line in lines:
            print(f"{Colors.DIM}  {line}{Colors.RESET}")

    @staticmethod
    def example(text: str) -> None:
        """Log example text."""
        print(f"  {Colors.GREEN}→{Colors.RESET} {Colors.BRIGHT}{text}{Colors.RESET}")

    @staticmethod
    def hint(text: str) -> None:
        """Log hint text."""
        print(f"\n{Colors.DIM}{text}{Colors.RESET}\n")

    @staticmethod
    def query(q: str) -> None:
        """Log user query."""
        print(f"\n{Colors.BG_BLUE}{Colors.WHITE} QUERY {Colors.RESET} {q}\n")

    @staticmethod
    def response(r: str) -> None:
        """Log response."""
        truncated = r[:500] + ("..." if len(r) > 500 else "")
        print(f"\n{Colors.GREEN}Response:{Colors.RESET} {truncated}\n")

    @staticmethod
    def api(step: str, msg_count: int) -> None:
        """Log API call step."""
        print(
            f"{Colors.DIM}[{timestamp()}]{Colors.RESET} {Colors.MAGENTA}◆{Colors.RESET} {step} ({msg_count} messages)"
        )

    @staticmethod
    def api_done(usage: dict) -> None:
        """Log API call completion with token usage."""
        if usage:
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            print(f"{Colors.DIM}         tokens: {input_tokens} in / {output_tokens} out{Colors.RESET}")

    @staticmethod
    def tool(name: str, args: dict) -> None:
        """Log tool call."""
        import json
        arg_str = json.dumps(args)
        truncated = arg_str[:100] + ("..." if len(arg_str) > 100 else "")
        print(f"{Colors.DIM}[{timestamp()}]{Colors.RESET} {Colors.YELLOW}⚡{Colors.RESET} {name} {Colors.DIM}{truncated}{Colors.RESET}")

    @staticmethod
    def tool_result(name: str, success: bool, output: str) -> None:
        """Log tool result."""
        icon = f"{Colors.GREEN}✓{Colors.RESET}" if success else f"{Colors.RED}✗{Colors.RESET}"
        truncated = output[:150] + ("..." if len(output) > 150 else "")
        print(f"{Colors.DIM}         {icon} {truncated}{Colors.RESET}")

    @staticmethod
    def gemini(action: str, detail: str = "") -> None:
        """Log Gemini API call."""
        print(f"{Colors.DIM}[{timestamp()}]{Colors.RESET} {Colors.BG_MAGENTA}{Colors.WHITE} GEMINI {Colors.RESET} {action}")
        if detail:
            print(f"{Colors.DIM}         {detail}{Colors.RESET}")

    @staticmethod
    def gemini_result(success: bool, msg: str) -> None:
        """Log Gemini result."""
        icon = f"{Colors.GREEN}✓{Colors.RESET}" if success else f"{Colors.RED}✗{Colors.RESET}"
        print(f"{Colors.DIM}         {icon} {msg}{Colors.RESET}")

    @staticmethod
    def vision(image_path: str, detail: str = "") -> None:
        """Log vision API call."""
        print(f"{Colors.DIM}[{timestamp()}]{Colors.RESET} {Colors.BG_BLUE}{Colors.WHITE} VISION {Colors.RESET} {image_path}")
        if detail:
            print(f"{Colors.DIM}         {detail}{Colors.RESET}")

    @staticmethod
    def vision_result(msg: str) -> None:
        """Log vision result."""
        truncated = msg[:150] + ("..." if len(msg) > 150 else "")
        print(f"{Colors.DIM}         ✓ {truncated}{Colors.RESET}")


# Default logger instance
log = Logger()
