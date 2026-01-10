"""
Session Recovery Hook.

Detects and recovers from corrupted sessions:
- Detects missing tool results after tool calls
- Injects synthetic tool_result blocks with status messages
- Enables graceful recovery
- Registered as post_tool_call hook
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Patterns that indicate a tool call failure or corruption
CORRUPTION_PATTERNS = [
    r"tool_result.*missing",
    r"no response from tool",
    r"tool call timed out",
    r"connection reset",
    r"unexpected end of.*response",
    r"malformed.*response",
    r"incomplete.*result",
    r"truncated.*output",
    r"<!DOCTYPE html>",  # HTML error pages
    r"<html>.*error",
    r"500 Internal Server Error",
    r"502 Bad Gateway",
    r"503 Service Unavailable",
    r"504 Gateway Timeout",
]

# Patterns indicating empty or null responses
EMPTY_RESPONSE_PATTERNS = [
    r"^\s*$",
    r"^null$",
    r"^undefined$",
    r"^None$",
    r"^\{\s*\}$",
    r"^\[\s*\]$",
]

# Tool-specific recovery strategies
TOOL_RECOVERY_STRATEGIES = {
    "invoke_gemini": "Model invocation failed. Try reducing prompt size or switching to a different model variant.",
    "invoke_openai": "Model invocation failed. Check authentication status with 'stravinsky auth status'.",
    "agent_spawn": "Agent spawn failed. Check if Claude CLI is available and properly configured.",
    "agent_output": "Agent output retrieval failed. The agent may still be running - try agent_progress first.",
    "grep_search": "Search failed. Verify the pattern syntax and directory path.",
    "ast_grep_search": "AST search failed. Ensure the language is supported and pattern is valid.",
    "lsp_hover": "LSP hover failed. The language server may not be running for this file type.",
    "session_read": "Session read failed. The session may have been corrupted or deleted.",
}

RECOVERY_NOTICE = """
> **[SESSION RECOVERY]**
> A tool result appears to be corrupted or incomplete.
> **Tool**: {tool_name}
> **Issue**: {issue}
> **Recovery**: {recovery_hint}
>
> The operation should be retried or an alternative approach should be used.
"""

SYNTHETIC_RESULT_TEMPLATE = """
[RECOVERED TOOL RESULT]
Status: FAILED - Corrupted or incomplete response detected
Tool: {tool_name}
Original output (truncated): {truncated_output}

Recovery Hint: {recovery_hint}

Recommended Actions:
1. Retry the tool call with the same or modified parameters
2. Check system health with get_system_health tool
3. If persistent, try an alternative approach
"""


def detect_corruption(output: str) -> str | None:
    """
    Detect if the output shows signs of corruption.

    Returns:
        Description of the corruption issue, or None if output appears valid
    """
    # Check for completely empty output
    if not output or output.strip() == "":
        return "Empty response received"

    # Check for empty response patterns
    for pattern in EMPTY_RESPONSE_PATTERNS:
        if re.match(pattern, output.strip(), re.IGNORECASE):
            return f"Empty or null response: {output[:50]}"

    # Check for corruption patterns
    for pattern in CORRUPTION_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            return f"Corruption pattern detected: {pattern}"

    # Check for extremely short responses that might indicate truncation
    # (only for tools that typically return substantial output)
    if len(output.strip()) < 10 and not output.strip().startswith(("{", "[", "true", "false")):
        # Could be truncated, but might also be valid short output
        # Only flag if it looks like truncated text
        if output.strip().endswith(("...", "---", "...)")):
            return "Response appears truncated"

    return None


def get_recovery_hint(tool_name: str, issue: str) -> str:
    """Get a recovery hint based on the tool and issue."""
    # Check for tool-specific strategy
    if tool_name in TOOL_RECOVERY_STRATEGIES:
        return TOOL_RECOVERY_STRATEGIES[tool_name]

    # Generic recovery hints based on issue type
    if "empty" in issue.lower():
        return "Retry the operation. If it persists, check if the resource exists."
    if "timeout" in issue.lower():
        return "The operation timed out. Try with smaller input or increase timeout."
    if "connection" in issue.lower():
        return "Network issue detected. Check connectivity and retry."
    if "500" in issue or "502" in issue or "503" in issue:
        return "Server error detected. Wait a moment and retry."
    if "truncated" in issue.lower():
        return "Response was truncated. Try requesting smaller chunks of data."

    return "Retry the operation or try an alternative approach."


async def session_recovery_hook(
    tool_name: str,
    arguments: dict[str, Any],
    output: str
) -> str | None:
    """
    Post-tool call hook that detects corrupted results and injects recovery information.

    Args:
        tool_name: Name of the tool that was called
        arguments: Arguments passed to the tool
        output: The output returned by the tool

    Returns:
        Modified output with recovery information, or None to keep original
    """
    # Detect corruption
    issue = detect_corruption(output)

    if not issue:
        return None

    logger.warning(f"[SessionRecovery] Corruption detected in {tool_name}: {issue}")

    # Get recovery hint
    recovery_hint = get_recovery_hint(tool_name, issue)

    # Truncate original output for display
    truncated_output = output[:200] + "..." if len(output) > 200 else output
    truncated_output = truncated_output.replace("\n", " ").strip()

    # Build synthetic result
    synthetic_result = SYNTHETIC_RESULT_TEMPLATE.format(
        tool_name=tool_name,
        truncated_output=truncated_output,
        recovery_hint=recovery_hint,
    )

    # Build recovery notice
    recovery_notice = RECOVERY_NOTICE.format(
        tool_name=tool_name,
        issue=issue,
        recovery_hint=recovery_hint,
    )

    # Return combined output
    recovered_output = synthetic_result + "\n" + recovery_notice

    logger.info(f"[SessionRecovery] Injected recovery guidance for {tool_name}")

    return recovered_output
