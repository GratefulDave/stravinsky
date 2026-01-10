#!/usr/bin/env python3
"""
UserPromptSubmit hook: Parallel execution reinforcement for subsequent prompts.

When Stravinsky mode is active, this hook reinforces parallel execution requirements
on EVERY subsequent prompt (not just the initial invocation).

Works with:
- parallel_execution.py: Initial activation and instruction injection
- todo_delegation.py: PostToolUse reminder after TodoWrite
"""

import json
import os
import sys
from pathlib import Path

STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"


def get_project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CWD", "."))


def get_todo_state() -> dict:
    todo_cache = get_project_dir() / ".claude" / "todo_state.json"
    if todo_cache.exists():
        try:
            return json.loads(todo_cache.read_text())
        except Exception:
            pass
    return {"todos": []}


def has_pending_todos() -> bool:
    state = get_todo_state()
    todos = state.get("todos", [])
    pending = [t for t in todos if t.get("status") == "pending"]
    return len(pending) >= 2


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    prompt = hook_input.get("prompt", "")

    if not STRAVINSKY_MODE_FILE.exists():
        print(prompt)
        return 0

    if not has_pending_todos():
        print(prompt)
        return 0

    reinforcement = """
<user-prompt-submit-hook>
[SYSTEM REMINDER - PARALLEL EXECUTION ACTIVE]

You have 2+ pending TODOs. When proceeding:

✅ SPAWN agents for ALL independent tasks in PARALLEL
✅ Use agent_spawn(agent_type="explore"|"dewey"|"frontend", prompt="...", description="...")
✅ Fire ALL agent_spawn calls in ONE response block
✅ Collect results with agent_output(task_id, block=true) after spawning

❌ DO NOT work sequentially on one task at a time
❌ DO NOT mark TODOs in_progress before spawning agents
❌ DO NOT use Task() tool (wrong for /strav - use agent_spawn)
❌ DO NOT use Read/Grep/Bash (use explore agents)

PARALLEL FIRST, then synthesize results.
</user-prompt-submit-hook>

---

"""
    print(reinforcement + prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
