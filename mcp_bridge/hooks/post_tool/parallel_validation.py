#!/usr/bin/env python3
"""
PostToolUse hook: Parallel Validation.

Tracks pending tasks after TodoWrite and sets a state flag if parallel
delegation is required. This state is consumed by the PreToolUse validator.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# State file base location (will be suffixed with session ID)
STATE_DIR = Path(".claude")


def get_state_file() -> Path:
    """Get path to state file, respecting CLAUDE_CWD and CLAUDE_SESSION_ID."""
    # Use environment variable passed by Claude Code
    cwd = Path(os.environ.get("CLAUDE_CWD", "."))
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
    # Sanitize session ID
    session_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    
    return cwd / ".claude" / f"parallel_state_{session_id}.json"


def save_state(state: Dict[str, Any]) -> None:
    """Save state to file."""
    path = get_state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def load_state() -> Dict[str, Any]:
    """Load state from file."""
    path = get_state_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def process_hook(hook_input: Dict[str, Any]) -> int:
    """Process the hook input and update state."""
    tool_name = hook_input.get("tool_name", "")
    
    # We only care about TodoWrite (creating tasks)
    # or maybe Task/agent_spawn (resetting the requirement)
    
    if tool_name == "TodoWrite":
        tool_input = hook_input.get("tool_input", {})
        todos = tool_input.get("todos", [])
        
        # Count independent pending todos
        # Conservative: assume all pending are independent for now
        pending_count = sum(1 for t in todos if t.get("status") == "pending")
        
        if pending_count >= 2:
            state = load_state()
            state.update({
                "delegation_required": True,
                "pending_count": pending_count,
                "last_todo_write": time.time(),
                "reason": f"TodoWrite created {pending_count} pending items. Parallel delegation required."
            })
            save_state(state)
            
    elif tool_name in ["Task", "agent_spawn"]:
        # If a task is spawned, we might be satisfying the requirement
        # But we need to spawn ONE for EACH independent task. 
        # For now, let's just note that a spawn happened.
        # The PreToolUse validator will decide if it's enough (maybe checking count?)
        # Or we can just decrement a counter?
        # Simpler: If ANY delegation happens, we assume the user is complying for now.
        # Strict implementation: We'd track how many spawned vs required.
        
        state = load_state()
        if state.get("delegation_required"):
            # Update state to reflect compliance
            state["delegation_required"] = False
            state["last_delegation"] = time.time()
            save_state(state)

    return 0


def main():
    try:
        hook_input = json.load(sys.stdin)
        exit_code = process_hook(hook_input)
        sys.exit(exit_code)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)


if __name__ == "__main__":
    main()
