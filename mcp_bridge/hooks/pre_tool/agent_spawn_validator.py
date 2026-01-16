#!/usr/bin/env python3
"""
PreToolUse hook: Agent Spawn Validator.

Blocks direct tools (Read, Grep, etc.) if parallel delegation is required
but hasn't happened yet.

Triggers when:
1. parallel_validation.py (PostToolUse) has set 'delegation_required=True'
2. User tries to use a non-delegation tool
3. Hard enforcement is enabled (opt-in)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# State file location
STATE_FILE = Path(".claude/parallel_state.json")
CONFIG_FILE = Path(".stravinsky/config.json") # Faster than yaml


def get_project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CWD", "."))


def get_state_file() -> Path:
    cwd = get_project_dir()
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
    # Sanitize session ID
    session_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return cwd / ".claude" / f"parallel_state_{session_id}.json"


def load_state() -> Dict[str, Any]:
    path = get_state_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def is_enforcement_enabled() -> bool:
    """Check if hard enforcement is enabled."""
    # Check env var override
    if os.environ.get("STRAVINSKY_ALLOW_SEQUENTIAL", "").lower() == "true":
        return False
        
    # Check config file (default: false for now)
    config_path = get_project_dir() / ".stravinsky/config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            return config.get("enforce_parallel_delegation", False)
        except Exception:
            pass
            
    return False


def process_hook(hook_input: Dict[str, Any]) -> int:
    """Process hook input."""
    tool_name = hook_input.get("toolName", "")
    
    # Allowed tools during delegation phase
    ALLOWED_TOOLS = ["Task", "agent_spawn", "TodoWrite", "TodoRead"]
    
    if tool_name in ALLOWED_TOOLS:
        return 0
        
    state = load_state()
    
    # If delegation is not required, allow
    if not state.get("delegation_required"):
        return 0
        
    # If hard enforcement is not enabled, allow (maybe warn? but PreToolUse warnings aren't visible usually)
    if not is_enforcement_enabled():
        # TODO: Ideally print a warning to stderr?
        return 0
        
    # BLOCK
    print(f"""
🛑 BLOCKED: PARALLEL DELEGATION REQUIRED

You have {state.get("pending_todos", "multiple")} pending tasks that require parallel execution.
You are attempting to use '{tool_name}' sequentially.

REQUIRED ACTION:
Spawn agents for ALL independent tasks in THIS response using:
- Task(subagent_type="...", prompt="...") 
- agent_spawn(agent_type="...", prompt="...")

To override (if tasks are truly dependent):
- Set STRAVINSKY_ALLOW_SEQUENTIAL=true
- Or use TodoWrite to update tasks to dependent state
""")
    return 2


def main():
    try:
        hook_input = json.load(sys.stdin)
        exit_code = process_hook(hook_input)
        sys.exit(exit_code)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)


if __name__ == "__main__":
    main()
