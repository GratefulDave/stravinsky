"""
Parallel Reinforcement V2 Hook - State-Based Parallel Execution Enforcement.

Combines dependency tracking + execution state tracking to provide
adaptive, context-aware parallel execution reinforcement.

This replaces the simpler parallel_reinforcement.py with a more intelligent
approach that:
1. Reads execution state to understand recent tool usage patterns
2. Reads dependency graph to identify independent tasks
3. Injects reinforcement only when degradation is detected
4. Uses progressively stronger language based on degradation severity

Based on GAP_ANALYSIS_PARALLEL_DELEGATION.md Option C (State-Based Reinforcement).
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Import sibling modules for state
from mcp_bridge.hooks.dependency_tracker import (
    DependencyGraph,
    get_parallel_delegation_prompt,
)
from mcp_bridge.hooks.execution_state_tracker import (
    ExecutionState,
    get_state_summary,
    needs_parallel_reminder,
    set_parallel_mode,
)

# State file locations
DEPENDENCY_STATE = Path.home() / ".stravinsky" / "task_dependencies.json"
EXECUTION_STATE = Path.home() / ".stravinsky" / "execution_state.json"


def _load_dependency_graph() -> DependencyGraph | None:
    """Load dependency graph from state file."""
    try:
        if DEPENDENCY_STATE.exists():
            data = json.loads(DEPENDENCY_STATE.read_text())
            return DependencyGraph.from_dict(data)
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _load_execution_state() -> ExecutionState | None:
    """Load execution state from state file."""
    try:
        if EXECUTION_STATE.exists():
            data = json.loads(EXECUTION_STATE.read_text())
            return ExecutionState.from_dict(data)
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _detect_parallel_trigger(prompt: str) -> bool:
    """Detect if prompt contains parallel mode triggers."""
    patterns = [
        r"/strav",
        r"/stravinsky",
        r"\bultrawork\b",
        r"\bulw\b",
        r"\buw\b",
        r"parallel\s+mode",
        r"spawn\s+agents?",
    ]
    prompt_lower = prompt.lower()
    return any(re.search(p, prompt_lower) for p in patterns)


def _get_reinforcement_level(state: ExecutionState) -> int:
    """
    Determine reinforcement intensity level (0-3).

    Level 0: No reinforcement needed
    Level 1: Gentle reminder (first occurrence)
    Level 2: Strong warning (2+ sequential patterns)
    Level 3: Critical alert (3+ sequential patterns or 5+ turns)
    """
    if not state.parallel_mode_active:
        return 0

    if state.pending_todos < 2:
        return 0

    # Check recent Task usage
    recent_5 = [t.lower() for t in state.recent_tools[:5]]
    has_recent_task = any("task" in t or "agent_spawn" in t for t in recent_5)

    if has_recent_task:
        return 0

    # Determine level based on degradation severity
    if state.sequential_pattern_count >= 3 or state.turns_since_agent_spawn >= 5:
        return 3
    elif state.sequential_pattern_count >= 2:
        return 2
    elif state.sequential_pattern_count >= 1 or state.turns_since_agent_spawn >= 3:
        return 1

    return 0


def _generate_reinforcement_prompt(
    level: int,
    state: ExecutionState,
    graph: DependencyGraph | None,
) -> str:
    """Generate reinforcement prompt based on level."""
    if level == 0:
        return ""

    # Get task info
    task_info = ""
    if graph and graph.independent_tasks:
        tasks = []
        for task_id in graph.independent_tasks[:5]:
            task = graph.tasks.get(task_id)
            if task:
                tasks.append(f"  • {task.content[:50]}...")
        task_info = "\n".join(tasks)

    if level == 1:
        # Gentle reminder
        return f"""
[💡 PARALLEL EXECUTION REMINDER]

You have {state.pending_todos} pending tasks. Consider spawning agents in parallel:

{task_info}

Pattern:
```python
agent_spawn(prompt="...", agent_type="explore", description="Task 1")
agent_spawn(prompt="...", agent_type="dewey", description="Task 2")
```
"""

    elif level == 2:
        # Strong warning
        return f"""
[⚠️ PARALLEL EXECUTION WARNING]

Sequential pattern detected ({state.sequential_pattern_count} occurrences).
You have {state.pending_todos} pending tasks that should run in parallel.

Independent tasks:
{task_info}

REQUIRED ACTION:
1. Spawn agent_spawn for EACH independent task
2. Fire ALL spawns in ONE response
3. Collect results with agent_output AFTER all spawns

DO NOT mark tasks in_progress before spawning agents.
"""

    else:  # level == 3
        # Critical alert
        return f"""
[🚨 CRITICAL: PARALLEL EXECUTION REQUIRED]

SEVERE degradation detected:
- Sequential patterns: {state.sequential_pattern_count}
- Turns since agent spawn: {state.turns_since_agent_spawn}
- Pending tasks: {state.pending_todos}

This is a HARD REQUIREMENT. You MUST spawn agents NOW.

Independent tasks requiring parallel execution:
{task_info}

EXECUTE IMMEDIATELY:
```python
# ALL of these in ONE response:
agent_spawn(prompt="Complete task 1", agent_type="explore", description="Task 1")
agent_spawn(prompt="Complete task 2", agent_type="explore", description="Task 2")
# ... spawn ALL pending tasks
```

FAILURE TO COMPLY will result in inefficient sequential execution.
"""


async def parallel_reinforcement_v2_hook(
    prompt: str,
    context: dict[str, Any] | None = None,
) -> str:
    """
    UserPromptSubmit hook that provides state-based parallel reinforcement.

    Args:
        prompt: The user's prompt
        context: Optional context dict

    Returns:
        Modified prompt with reinforcement if needed, original prompt otherwise
    """
    # Check for parallel mode triggers in prompt
    if _detect_parallel_trigger(prompt):
        set_parallel_mode(True)

    # Load current state
    state = _load_execution_state()
    if not state:
        return prompt

    # Load dependency graph
    graph = _load_dependency_graph()

    # Determine reinforcement level
    level = _get_reinforcement_level(state)

    if level == 0:
        return prompt

    # Generate reinforcement
    reinforcement = _generate_reinforcement_prompt(level, state, graph)

    if reinforcement:
        logger.info(f"[ParallelReinforcementV2] Injecting level {level} reinforcement")
        return reinforcement + "\n---\n\n" + prompt

    return prompt


def main():
    """CLI entry point for UserPromptSubmit hook."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    prompt = hook_input.get("prompt", "")

    # Check for parallel mode triggers
    if _detect_parallel_trigger(prompt):
        set_parallel_mode(True)

    # Load state
    state = _load_execution_state()
    if not state:
        print(prompt)
        return 0

    # Load dependency graph
    graph = _load_dependency_graph()

    # Determine reinforcement level
    level = _get_reinforcement_level(state)

    if level == 0:
        print(prompt)
        return 0

    # Generate and inject reinforcement
    reinforcement = _generate_reinforcement_prompt(level, state, graph)

    if reinforcement:
        logger.info(f"[ParallelReinforcementV2] Injecting level {level} reinforcement")
        modified_prompt = reinforcement + "\n---\n\n" + prompt
        print(modified_prompt)
    else:
        print(prompt)

    return 0


if __name__ == "__main__":
    sys.exit(main())
