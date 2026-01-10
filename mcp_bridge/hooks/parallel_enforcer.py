"""
Parallel Enforcer Hook - Enforce Parallel Agent Spawning.

Detects when 2+ independent tasks exist and injects reminders
to spawn agents in parallel rather than working sequentially.

Based on oh-my-opencode's parallel execution enforcement pattern.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Parallel enforcement prompt
PARALLEL_ENFORCEMENT_PROMPT = """
[PARALLEL EXECUTION REQUIRED]

You have {count} independent pending tasks. You MUST spawn agents for ALL of them simultaneously.

CORRECT (Parallel - DO THIS):
```
agent_spawn(prompt="Task 1...", agent_type="explore", description="Task 1")
agent_spawn(prompt="Task 2...", agent_type="explore", description="Task 2")
agent_spawn(prompt="Task 3...", agent_type="dewey", description="Task 3")
// All spawned in ONE response, then wait for results
```

WRONG (Sequential - DO NOT DO THIS):
```
Mark task 1 in_progress -> work on it -> complete
Mark task 2 in_progress -> work on it -> complete  // TOO SLOW!
```

RULES:
1. Spawn ALL independent tasks simultaneously using agent_spawn
2. Do NOT mark any task as in_progress until agents are spawned
3. Collect results with agent_output AFTER spawning
4. Only work sequentially when tasks have dependencies
"""

# Track if enforcement was already triggered this session
_enforcement_triggered: dict[str, bool] = {}


async def parallel_enforcer_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Post-tool-call hook that triggers after TodoWrite.

    When 2+ pending todos are detected, injects parallel execution
    enforcement prompt to prevent sequential work patterns.
    """
    tool_name = params.get("tool_name", "")
    output = params.get("output", "")
    session_id = params.get("session_id", "default")

    # Only trigger for TodoWrite calls
    if tool_name.lower() not in ["todowrite", "todo_write"]:
        return None

    # Count pending todos
    pending_count = _count_pending_todos(output)

    if pending_count < 2:
        return None

    # Check if already triggered recently
    if _enforcement_triggered.get(session_id, False):
        return None

    # Mark as triggered
    _enforcement_triggered[session_id] = True

    logger.info(f"[ParallelEnforcerHook] Detected {pending_count} pending todos, enforcing parallel execution")

    # Inject enforcement prompt
    enforcement = PARALLEL_ENFORCEMENT_PROMPT.format(count=pending_count)
    modified_output = output + "\n\n" + enforcement

    return modified_output


def _count_pending_todos(output: str) -> int:
    """Count the number of pending todos in TodoWrite output."""
    # Pattern matches various pending todo formats
    patterns = [
        r'\[pending\]',
        r'"status":\s*"pending"',
        r"status:\s*pending",
        r"'status':\s*'pending'",
    ]

    total = 0
    for pattern in patterns:
        matches = re.findall(pattern, output, re.IGNORECASE)
        total += len(matches)

    return total


def reset_enforcement(session_id: str = "default"):
    """Reset enforcement state for a session."""
    _enforcement_triggered[session_id] = False


async def parallel_enforcer_post_tool_hook(
    tool_name: str,
    arguments: dict[str, Any],
    output: str
) -> str | None:
    """
    Post-tool-call hook interface for HookManager.

    Wraps parallel_enforcer_hook for the standard hook signature.
    """
    params = {
        "tool_name": tool_name,
        "arguments": arguments,
        "output": output,
    }

    result = await parallel_enforcer_hook(params)

    if isinstance(result, str):
        return result
    return None
