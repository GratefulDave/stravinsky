#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"


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
        "parallel_mode_active": False,
        "last_task_spawn_index": -1,
        "last_10_tools": [],
        "pending_todos": 0,
    }


def get_dependency_graph():
    graph_file = get_project_dir() / ".claude/task_dependencies.json"
    if graph_file.exists():
        try:
            return json.loads(graph_file.read_text())
        except Exception:
            pass
    return {"dependencies": {}}


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    prompt = hook_input.get("prompt", "")

    if not STRAVINSKY_MODE_FILE.exists():
        print(prompt)
        return 0

    state = get_execution_state()

    if not state.get("parallel_mode_active", False):
        print(prompt)
        return 0

    last_task_index = state.get("last_task_spawn_index", -1)
    current_index = len(state.get("last_10_tools", []))
    turns_since_task = current_index - last_task_index - 1

    if turns_since_task < 2:
        print(prompt)
        return 0

    graph = get_dependency_graph()
    dependencies = graph.get("dependencies", {})
    independent_tasks = [
        tid for tid, info in dependencies.items() if info.get("independent", False)
    ]

    if len(independent_tasks) < 2:
        print(prompt)
        return 0

    reinforcement = f"""
<user-prompt-submit-hook>
[SYSTEM REMINDER - PARALLEL EXECUTION DEGRADATION DETECTED]

Analysis:
- {state.get("pending_todos", 0)} pending TODOs
- {len(independent_tasks)} independent tasks identified
- {turns_since_task} turns since last Task() spawn
- Risk: Sequential execution fallback

REQUIRED ACTION - Spawn agents for ALL independent tasks NOW:

Independent tasks: {", ".join(independent_tasks[:5])}

Pattern:
```
Task(subagent_type="explore", prompt="...", description="task_1")
Task(subagent_type="dewey", prompt="...", description="task_2")
...
```

DO NOT:
- Mark TODOs in_progress before spawning agents
- Work sequentially on one task at a time
- Use Read/Grep/Bash directly (BLOCKED in stravinsky mode)

SPAWN ALL TASK() AGENTS IN THIS SAME RESPONSE.
</user-prompt-submit-hook>

---

"""
    print(reinforcement + prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
