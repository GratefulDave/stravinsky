#!/usr/bin/env python3
"""
Stravinsky Mode Enforcer Hook

This PreToolUse hook blocks native file reading tools (Read, Search, Grep, Bash)
when stravinsky orchestrator mode is active, forcing use of agent_spawn instead.

Stravinsky mode is activated by creating a marker file:
  ~/.stravinsky_mode

The /strav:stravinsky command should create this file, and it should be
removed when the task is complete.

Exit codes:
  0 = Allow the tool to execute
  2 = Block the tool (reason sent via stderr)
"""

import json
import os
import sys
from pathlib import Path

# Marker file that indicates stravinsky mode is active
STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"

# Tools to block when in stravinsky mode
BLOCKED_TOOLS = {
    "Read",
    "Search", 
    "Grep",
    "Bash",
    "MultiEdit",
    "Edit",
}

# Tools that are always allowed
ALLOWED_TOOLS = {
    "TodoRead",
    "TodoWrite",
    "Task",
    "Agent",  # MCP agent tools should be allowed
}


def is_stravinsky_mode_active() -> bool:
    """Check if stravinsky orchestrator mode is active."""
    return STRAVINSKY_MODE_FILE.exists()


def read_stravinsky_mode_config() -> dict:
    """Read the stravinsky mode configuration if it exists."""
    if not STRAVINSKY_MODE_FILE.exists():
        return {}
    try:
        return json.loads(STRAVINSKY_MODE_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return {"active": True}


def main():
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # If we can't parse input, allow the tool
        sys.exit(0)
    
    tool_name = hook_input.get("tool_name", "")
    
    # Always allow certain tools
    if tool_name in ALLOWED_TOOLS:
        sys.exit(0)
    
    # Check if stravinsky mode is active
    if not is_stravinsky_mode_active():
        # Not in stravinsky mode, allow all tools
        sys.exit(0)
    
    config = read_stravinsky_mode_config()
    
    # Check if this tool should be blocked
    if tool_name in BLOCKED_TOOLS:
        # Block the tool and tell Claude why
        reason = f"""⚠️ STRAVINSKY MODE ACTIVE - {tool_name} BLOCKED

You are in Stravinsky orchestrator mode. Native tools are disabled.

Instead of using {tool_name}, you MUST use:
  - stravinsky:agent_spawn with agent_type="explore" for file reading/searching
  - stravinsky:agent_spawn with agent_type="dewey" for documentation

Example:
  agent_spawn(agent_type="explore", prompt="Read and analyze the file at path/to/file.py")

To exit stravinsky mode, run:
  rm ~/.stravinsky_mode
"""
        # Send reason to stderr (Claude sees this)
        print(reason, file=sys.stderr)
        # Exit with code 2 to block the tool
        sys.exit(2)
    
    # Tool not in block list, allow it
    sys.exit(0)


if __name__ == "__main__":
    main()
