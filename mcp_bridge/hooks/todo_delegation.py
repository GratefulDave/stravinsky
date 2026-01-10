#!/usr/bin/env python3
"""
PostToolUse hook for TodoWrite: CRITICAL parallel execution enforcer.

This hook fires AFTER TodoWrite completes. If there are 2+ pending items,
it outputs a STRONG reminder that Task agents must be spawned immediately.

Exit code 2 is used to signal a HARD BLOCK - Claude should see this as
a failure condition requiring immediate correction.

Works in tandem with:
- parallel_execution.py (UserPromptSubmit): Pre-emptive instruction injection
- stravinsky_mode.py (PreToolUse): Hard blocking of Read/Grep/Bash tools
"""

import json
import sys
from pathlib import Path

# Check if stravinsky mode is active (hard blocking enabled)
STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"


def is_stravinsky_mode():
    """Check if hard blocking mode is active."""
    return STRAVINSKY_MODE_FILE.exists()


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")

    if tool_name != "TodoWrite":
        return 0

    # Get the todos that were just written
    tool_input = hook_input.get("tool_input", {})
    todos = tool_input.get("todos", [])

    # Count pending todos
    pending_count = sum(1 for t in todos if t.get("status") == "pending")

    if pending_count < 2:
        return 0

    # Check if stravinsky mode is active
    stravinsky_active = is_stravinsky_mode()

    # CRITICAL: Output urgent reminder for parallel Task spawning
    mode_warning = ""
    if stravinsky_active:
        mode_warning = """
⚠️ STRAVINSKY MODE ACTIVE - Direct tools (Read, Grep, Bash) are BLOCKED.
   You MUST use Task(subagent_type="explore", ...) for ALL file operations.
"""

    error_message = f"""
🚨 PARALLEL DELEGATION REQUIRED 🚨

TodoWrite created {pending_count} pending items.
{mode_warning}
You MUST spawn Task agents for ALL independent TODOs in THIS SAME RESPONSE.

Required pattern (IMMEDIATELY after this message):
Task(subagent_type="explore", prompt="TODO 1...", description="TODO 1", run_in_background=true)
Task(subagent_type="explore", prompt="TODO 2...", description="TODO 2", run_in_background=true)
...

DO NOT:
- End your response without spawning Tasks
- Mark TODOs in_progress before spawning Tasks
- Use Read/Grep/Bash directly (BLOCKED in stravinsky mode)

Your NEXT action MUST be multiple Task() calls, one for each independent TODO.
"""
    # CRITICAL: Output to stdout so Claude sees the message
    # stderr is not reliably injected into the conversation
    print(error_message)

    # Exit code 2 = HARD BLOCK in stravinsky mode
    # Exit code 1 = WARNING otherwise
    return 2 if stravinsky_active else 1


if __name__ == "__main__":
    sys.exit(main())
