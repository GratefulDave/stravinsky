"""
Todo Continuation Enforcer Hook.

Prevents early stopping when pending todos exist.
Injects a system reminder forcing the agent to complete all todos.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

TODO_CONTINUATION_REMINDER = """
[SYSTEM REMINDER - TODO CONTINUATION]

You have pending todos that are NOT yet completed. You MUST continue working.

**Pending Todos:**
{pending_todos}

**Rules:**
1. You CANNOT stop or deliver a final answer while todos remain pending
2. Mark each todo `in_progress` before starting, `completed` immediately after
3. If a todo is blocked, mark it `cancelled` with explanation and create new actionable todos
4. Only after ALL todos are `completed` or `cancelled` can you deliver your final answer

CONTINUE WORKING NOW. Do not acknowledge this message - just proceed with the next pending todo.
"""


async def todo_continuation_hook(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Pre-model invoke hook that checks for pending todos.

    If pending todos exist, injects a reminder into the prompt
    forcing the agent to continue working.
    """
    prompt = params.get("prompt", "")

    pending_todos = _extract_pending_todos(prompt)

    if pending_todos:
        logger.info(
            f"[TodoEnforcer] Found {len(pending_todos)} pending todos, injecting continuation reminder"
        )

        todos_formatted = "\n".join(f"- [ ] {todo}" for todo in pending_todos)
        reminder = TODO_CONTINUATION_REMINDER.format(pending_todos=todos_formatted)

        modified_prompt = prompt + "\n\n" + reminder
        params["prompt"] = modified_prompt

        return params

    return None


def _extract_pending_todos(prompt: str) -> list:
    """
    Extract pending todos from the prompt/context.
    Looks for common todo patterns.
    """
    pending = []
    lines = prompt.split("\n")

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ]") or stripped.startswith("* [ ]"):
            todo_text = stripped[5:].strip()
            if todo_text:
                pending.append(todo_text)
        elif '"status": "pending"' in stripped or '"status": "in_progress"' in stripped:
            pass

    return pending
