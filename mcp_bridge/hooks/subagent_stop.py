#!/usr/bin/env python3
"""
SubagentStop hook: Handler for agent/subagent completion events.

Fires when a Claude Code subagent (Task tool) finishes to:
1. Output completion status messages
2. Verify agent produced expected output
3. Block completion if critical validation fails
4. Integrate with TODO tracking

Exit codes:
  0 = Allow completion
  2 = Block completion (force continuation)
"""

import json
import sys
from pathlib import Path
from typing import Optional, Tuple


STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"


def is_stravinsky_mode() -> bool:
    """Check if stravinsky mode is active."""
    return STRAVINSKY_MODE_FILE.exists()


def extract_subagent_info(hook_input: dict) -> Tuple[str, str, str]:
    """
    Extract subagent information from hook input.

    Returns: (agent_type, description, status)
    """
    # Try to get from tool parameters or response
    params = hook_input.get("tool_input", hook_input.get("params", {}))
    response = hook_input.get("tool_response", "")

    agent_type = params.get("subagent_type", "unknown")
    description = params.get("description", "")[:50]

    # Determine status from response
    status = "completed"
    response_lower = response.lower() if isinstance(response, str) else ""
    if "error" in response_lower or "failed" in response_lower:
        status = "failed"
    elif "timeout" in response_lower:
        status = "timeout"

    return agent_type, description, status


def format_completion_message(agent_type: str, description: str, status: str) -> str:
    """Format user-friendly completion message."""
    icon = "✓" if status == "completed" else "✗"
    return f"{icon} Subagent {agent_type} {status}: {description}"


def should_block(status: str, agent_type: str) -> bool:
    """
    Determine if we should block completion.

    Block if:
    - Agent failed AND stravinsky mode active AND critical agent type
    """
    if status != "completed" and is_stravinsky_mode():
        critical_agents = {"delphi", "code-reviewer", "debugger"}
        if agent_type in critical_agents:
            return True
    return False


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    # Extract subagent info
    agent_type, description, status = extract_subagent_info(hook_input)

    # Output completion message
    message = format_completion_message(agent_type, description, status)
    print(message, file=sys.stderr)

    # Check if we should block
    if should_block(status, agent_type):
        print(f"\n⚠️ CRITICAL SUBAGENT FAILURE - {agent_type} failed", file=sys.stderr)
        print("Review the error and retry or delegate to delphi.", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
