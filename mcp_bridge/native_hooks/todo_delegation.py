#!/usr/bin/env python3
"""
PostToolUse hook for TodoWrite: Enforces parallel delegation.

After TodoWrite is called, this hook injects a reminder to spawn
parallel Task agents for all independent TODOs.
"""
import json
import sys


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

    # Output the parallel delegation reminder
    reminder = f"""
[PARALLEL DELEGATION REQUIRED]

You just created {pending_count} pending TODOs. Before your NEXT response:

1. Identify which TODOs are INDEPENDENT (can run simultaneously)
2. For EACH independent TODO, spawn a Task agent:
   Task(subagent_type="Explore", prompt="[TODO details]", run_in_background=true)
3. Fire ALL Task calls in ONE response - do NOT wait between them
4. Do NOT mark any TODO as in_progress until agents return

WRONG: Create TODO list -> Mark TODO 1 in_progress -> Work -> Complete -> Repeat
CORRECT: Create TODO list -> Spawn Task for each -> Collect results -> Mark complete
"""
    print(reminder)
    return 0


if __name__ == "__main__":
    sys.exit(main())
