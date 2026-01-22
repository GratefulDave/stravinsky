"""
Dependency Tracker Hook - Parse TODOs for Task Dependencies.

Maintains a persistent task dependency graph by parsing TODO content for
dependency signals (keywords like "after", "depends on", "requires", etc.)
and parallel markers ("also", "meanwhile", "simultaneously").

Based on GAP_ANALYSIS_PARALLEL_DELEGATION.md Option C recommendation.

Files:
- State file: ~/.stravinsky/task_dependencies.json
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# State file location
STATE_FILE = Path.home() / ".stravinsky" / "task_dependencies.json"

# Dependency keyword patterns
DEPENDENCY_PATTERNS = [
    (r"\bafter\b", "sequential"),
    (r"\bdepends?\s+on\b", "dependency"),
    (r"\brequires?\b", "dependency"),
    (r"\bonce\b", "sequential"),
    (r"\bwhen\b", "conditional"),
    (r"\bthen\b", "sequential"),
    (r"\bnext\b", "sequential"),
    (r"\bfinally\b", "sequential"),
    (r"\bbefore\b", "dependency"),  # Reverse dependency
]

# Parallel markers - indicate independence
PARALLEL_PATTERNS = [
    (r"\balso\b", "parallel"),
    (r"\bmeanwhile\b", "parallel"),
    (r"\bsimultaneously\b", "parallel"),
    (r"\bin\s+parallel\b", "parallel"),
    (r"\b\[parallel\]\b", "explicit_parallel"),  # Manual override
    (r"\bindependent\b", "independent"),
]


@dataclass
class TaskDependency:
    """Represents a task with its dependencies."""

    task_id: str
    content: str
    status: str
    dependencies: list[str] = field(default_factory=list)
    is_independent: bool = True
    markers: list[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    """Full dependency graph for all tasks."""

    tasks: dict[str, TaskDependency] = field(default_factory=dict)
    independent_tasks: list[str] = field(default_factory=list)
    dependent_tasks: list[str] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "tasks": {k: asdict(v) for k, v in self.tasks.items()},
            "independent_tasks": self.independent_tasks,
            "dependent_tasks": self.dependent_tasks,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DependencyGraph:
        """Create from dict."""
        tasks = {}
        for k, v in data.get("tasks", {}).items():
            tasks[k] = TaskDependency(**v)
        return cls(
            tasks=tasks,
            independent_tasks=data.get("independent_tasks", []),
            dependent_tasks=data.get("dependent_tasks", []),
            last_updated=data.get("last_updated", ""),
        )


def _detect_dependency_markers(content: str) -> tuple[list[str], bool]:
    """
    Detect dependency and parallel markers in task content.

    Returns:
        Tuple of (list of markers found, is_independent)
    """
    content_lower = content.lower()
    markers = []
    has_dependency = False
    has_parallel = False

    # Check dependency patterns
    for pattern, marker_type in DEPENDENCY_PATTERNS:
        if re.search(pattern, content_lower):
            markers.append(marker_type)
            has_dependency = True

    # Check parallel patterns
    for pattern, marker_type in PARALLEL_PATTERNS:
        if re.search(pattern, content_lower):
            markers.append(marker_type)
            has_parallel = True

    # Explicit parallel overrides dependencies
    if "explicit_parallel" in markers or "independent" in markers:
        return markers, True

    # If has dependency markers but no parallel markers -> dependent
    # If has parallel markers -> independent
    # If no markers -> default to independent (conservative)
    is_independent = not has_dependency or has_parallel

    return markers, is_independent


def _load_graph() -> DependencyGraph:
    """Load dependency graph from state file."""
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            return DependencyGraph.from_dict(data)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"[DependencyTracker] Failed to load state: {e}")

    return DependencyGraph()


def _save_graph(graph: DependencyGraph) -> None:
    """Save dependency graph to state file."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        from datetime import datetime

        graph.last_updated = datetime.now().isoformat()
        STATE_FILE.write_text(json.dumps(graph.to_dict(), indent=2))
    except OSError as e:
        logger.warning(f"[DependencyTracker] Failed to save state: {e}")


def parse_todos_from_input(todo_input: list[dict[str, Any]]) -> list[TaskDependency]:
    """Parse TODO list input into TaskDependency objects."""
    tasks = []

    for i, todo in enumerate(todo_input):
        content = todo.get("content", "")
        status = todo.get("status", "pending")
        task_id = f"todo_{i}"

        markers, is_independent = _detect_dependency_markers(content)

        task = TaskDependency(
            task_id=task_id,
            content=content,
            status=status,
            dependencies=[],
            is_independent=is_independent,
            markers=markers,
        )
        tasks.append(task)

    return tasks


def update_dependency_graph(todos: list[dict[str, Any]]) -> DependencyGraph:
    """
    Update the dependency graph from a list of TODOs.

    Args:
        todos: List of TODO dicts with content and status

    Returns:
        Updated DependencyGraph
    """
    graph = _load_graph()

    # Parse new todos
    tasks = parse_todos_from_input(todos)

    # Update graph
    graph.tasks = {t.task_id: t for t in tasks}
    graph.independent_tasks = [
        t.task_id for t in tasks if t.is_independent and t.status == "pending"
    ]
    graph.dependent_tasks = [
        t.task_id for t in tasks if not t.is_independent and t.status == "pending"
    ]

    # Save updated graph
    _save_graph(graph)

    logger.info(
        f"[DependencyTracker] Updated graph: "
        f"{len(graph.independent_tasks)} independent, "
        f"{len(graph.dependent_tasks)} dependent"
    )

    return graph


def get_independent_tasks() -> list[str]:
    """Get list of independent task IDs from the current graph."""
    graph = _load_graph()
    return graph.independent_tasks


def get_parallel_delegation_prompt(graph: DependencyGraph) -> str | None:
    """
    Generate a parallel delegation prompt if there are 2+ independent tasks.

    Returns:
        Prompt string if parallel delegation needed, None otherwise
    """
    if len(graph.independent_tasks) < 2:
        return None

    task_list = []
    for task_id in graph.independent_tasks:
        task = graph.tasks.get(task_id)
        if task:
            task_list.append(f"  - {task.content[:60]}...")

    task_str = "\n".join(task_list)

    return f"""
[SYSTEM REMINDER - PARALLEL DELEGATION REQUIRED]

Independent tasks detected ({len(graph.independent_tasks)} tasks):
{task_str}

You MUST spawn agents for these tasks IN PARALLEL:

```python
# Spawn ALL independent tasks simultaneously
agent_spawn(prompt="...", agent_type="explore", description="todo_0")
agent_spawn(prompt="...", agent_type="explore", description="todo_1")
# ... spawn all independent tasks
```

Dependent tasks can run after their dependencies complete.
"""


async def dependency_tracker_post_tool_hook(
    tool_name: str,
    arguments: dict[str, Any],
    output: str,
) -> str | None:
    """
    Post-tool-call hook interface for HookManager.

    Triggers after TodoWrite to update dependency graph.
    """
    if tool_name.lower() not in ["todowrite", "todo_write"]:
        return None

    # Extract todos from arguments
    todos = arguments.get("todos", [])
    if not todos:
        return None

    # Update graph
    graph = update_dependency_graph(todos)

    # Generate prompt if parallel delegation needed
    prompt = get_parallel_delegation_prompt(graph)
    if prompt:
        return output + "\n\n" + prompt

    return None


def main():
    """CLI entry point for UserPromptSubmit hook."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    prompt = hook_input.get("prompt", "")

    # Check if there are independent tasks that need parallel delegation
    graph = _load_graph()

    if len(graph.independent_tasks) >= 2:
        delegation_prompt = get_parallel_delegation_prompt(graph)
        if delegation_prompt:
            # Inject reminder before prompt
            modified_prompt = delegation_prompt + "\n---\n\n" + prompt
            print(modified_prompt)
            return 0

    # No modification needed
    print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
