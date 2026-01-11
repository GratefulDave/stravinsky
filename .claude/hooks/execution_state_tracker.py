#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from datetime import datetime


def get_project_dir():
    return Path(os.environ.get("CLAUDE_CWD", "."))


def get_execution_state():
    state_file = get_project_dir() / ".claude/execution_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass

    return {
        "last_10_tools": [],
        "last_task_spawn_index": -1,
        "pending_todos": 0,
        "parallel_mode_active": False,
        "last_updated": None,
    }


def save_execution_state(state):
    state_file = get_project_dir() / ".claude/execution_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().isoformat()
    state_file.write_text(json.dumps(state, indent=2))


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")

    state = get_execution_state()
    state["last_10_tools"].append(tool_name)
    state["last_10_tools"] = state["last_10_tools"][-10:]

    if tool_name == "Task":
        try:
            index = len(state["last_10_tools"]) - 1
            state["last_task_spawn_index"] = index
        except:
            pass

    if tool_name == "TodoWrite":
        tool_input = hook_input.get("tool_input", {})
        todos = tool_input.get("todos", [])
        pending = sum(1 for t in todos if t.get("status") == "pending")
        state["pending_todos"] = pending
        state["parallel_mode_active"] = pending >= 2

    save_execution_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
