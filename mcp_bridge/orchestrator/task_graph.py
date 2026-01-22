"""
Task Graph and Parallel Execution Enforcer

This module provides hard enforcement of parallel execution for independent tasks.
Tasks declared as independent MUST be spawned in parallel, or execution is blocked.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a task in the execution graph."""

    PENDING = "pending"
    SPAWNED = "spawned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """A task in the execution graph."""

    id: str
    description: str
    agent_type: str
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    spawn_time: float | None = None
    task_id: str | None = None  # The agent task ID once spawned


@dataclass
class TaskGraph:
    """
    Directed Acyclic Graph of tasks with dependency tracking.

    Tasks with no dependencies (or whose dependencies are all complete)
    are considered "ready" and MUST be spawned in parallel.
    """

    tasks: dict[str, Task] = field(default_factory=dict)

    def add_task(
        self,
        task_id: str,
        description: str,
        agent_type: str,
        dependencies: list[str] | None = None,
    ) -> Task:
        """Add a task to the graph."""
        task = Task(
            id=task_id,
            description=description,
            agent_type=agent_type,
            dependencies=dependencies or [],
        )
        self.tasks[task_id] = task
        return task

    def get_ready_tasks(self) -> list[Task]:
        """
        Get all tasks that are ready to execute.

        A task is ready if:
        1. It has PENDING status
        2. All its dependencies are COMPLETED
        """
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are complete
            deps_complete = all(
                self.tasks.get(dep_id, Task(id=dep_id, description="", agent_type="")).status
                == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )

            if deps_complete:
                ready.append(task)

        return ready

    def get_independent_groups(self) -> list[list[Task]]:
        """
        Get groups of tasks that can run in parallel.

        Returns a list of "waves" - each wave contains tasks that:
        1. Have all dependencies satisfied
        2. Can run concurrently with each other
        """
        waves: list[list[Task]] = []
        completed_ids: set[str] = set()

        # Simulate execution waves
        remaining = set(self.tasks.keys())

        while remaining:
            wave = []
            for task_id in list(remaining):
                task = self.tasks[task_id]
                # Check if all dependencies are in completed set
                if all(dep in completed_ids for dep in task.dependencies):
                    wave.append(task)

            if not wave:
                # Circular dependency or error
                logger.error(f"Circular dependency detected. Remaining: {remaining}")
                break

            waves.append(wave)
            for task in wave:
                completed_ids.add(task.id)
                remaining.discard(task.id)

        return waves

    def mark_spawned(self, task_id: str, agent_task_id: str) -> None:
        """Mark a task as spawned with its agent task ID."""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.SPAWNED
            self.tasks[task_id].spawn_time = time.time()
            self.tasks[task_id].task_id = agent_task_id

    def mark_completed(self, task_id: str) -> None:
        """Mark a task as completed."""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED

    def mark_failed(self, task_id: str) -> None:
        """Mark a task as failed."""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.FAILED

    @classmethod
    def from_dict(cls, data: dict) -> TaskGraph:
        """
        Create a TaskGraph from a dictionary.

        Expected format:
        {
            "task_a": {"description": "...", "agent_type": "explore", "depends_on": []},
            "task_b": {"description": "...", "agent_type": "dewey", "depends_on": []},
            "task_c": {"description": "...", "agent_type": "frontend", "depends_on": ["task_a", "task_b"]}
        }
        """
        graph = cls()
        for task_id, task_data in data.items():
            graph.add_task(
                task_id=task_id,
                description=task_data.get("description", ""),
                agent_type=task_data.get("agent_type", "explore"),
                dependencies=task_data.get("depends_on", []),
            )
        return graph

    def to_dict(self) -> dict:
        """Serialize the graph to a dictionary."""
        return {
            task_id: {
                "description": task.description,
                "agent_type": task.agent_type,
                "depends_on": task.dependencies,
                "status": task.status.value,
            }
            for task_id, task in self.tasks.items()
        }


class ParallelExecutionError(Exception):
    """Raised when parallel execution rules are violated."""

    pass


@dataclass
class DelegationEnforcer:
    """
    Enforces parallel execution of independent tasks.

    This enforcer tracks agent spawns and validates that independent tasks
    are spawned within a time window (indicating parallel execution).
    """

    task_graph: TaskGraph
    parallel_window_ms: float = 500  # Max time between parallel spawns
    strict: bool = True  # If True, raise errors on violations

    _spawn_batch: list[tuple[str, float]] = field(default_factory=list)
    _current_wave: int = 0
    _waves: list[list[Task]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize the execution waves."""
        self._waves = self.task_graph.get_independent_groups()
        logger.info(f"[DelegationEnforcer] Initialized with {len(self._waves)} execution waves")
        for i, wave in enumerate(self._waves):
            task_ids = [t.id for t in wave]
            logger.info(f"  Wave {i + 1}: {task_ids}")

    def get_current_wave(self) -> list[Task]:
        """Get the current wave of tasks that should be spawned."""
        if self._current_wave < len(self._waves):
            return self._waves[self._current_wave]
        return []

    def validate_spawn(self, task_id: str) -> tuple[bool, str | None]:
        """
        Validate that a task spawn is allowed.

        Returns (is_valid, error_message).
        """
        if task_id not in self.task_graph.tasks:
            return False, f"Unknown task: {task_id}"

        task = self.task_graph.tasks[task_id]
        current_wave = self.get_current_wave()
        current_wave_ids = {t.id for t in current_wave}

        # Check if this task is in the current wave
        if task_id not in current_wave_ids:
            # Check if it's a future wave task being spawned too early
            for future_wave in self._waves[self._current_wave + 1 :]:
                if task_id in {t.id for t in future_wave}:
                    return False, (
                        f"Task '{task_id}' has unmet dependencies. "
                        f"Current wave tasks: {list(current_wave_ids)}"
                    )
            return False, f"Task '{task_id}' not found in any wave"

        return True, None

    def record_spawn(self, task_id: str, agent_task_id: str) -> None:
        """Record that a task was spawned."""
        now = time.time()
        self._spawn_batch.append((task_id, now))
        self.task_graph.mark_spawned(task_id, agent_task_id)

        logger.info(f"[DelegationEnforcer] Recorded spawn: {task_id} -> {agent_task_id}")

    def check_parallel_compliance(self) -> tuple[bool, str | None]:
        """
        Check if the current wave was spawned in parallel.

        Should be called after all tasks in a wave are spawned.
        Returns (is_compliant, error_message).
        """
        current_wave = self.get_current_wave()
        if len(current_wave) <= 1:
            # Single task waves don't need parallel check
            return True, None

        current_wave_ids = {t.id for t in current_wave}
        wave_spawns = [(tid, ts) for tid, ts in self._spawn_batch if tid in current_wave_ids]

        if len(wave_spawns) < len(current_wave):
            # Not all tasks spawned yet
            missing = current_wave_ids - {tid for tid, _ in wave_spawns}
            return False, f"Missing spawns for wave: {missing}"

        # Check time window
        spawn_times = [ts for _, ts in wave_spawns]
        time_spread_ms = (max(spawn_times) - min(spawn_times)) * 1000

        if time_spread_ms > self.parallel_window_ms:
            return False, (
                f"Tasks in wave were not spawned in parallel. "
                f"Time spread: {time_spread_ms:.0f}ms > {self.parallel_window_ms}ms limit. "
                f"Independent tasks MUST be spawned simultaneously."
            )

        logger.info(
            f"[DelegationEnforcer] Wave {self._current_wave + 1} spawned in parallel "
            f"(spread: {time_spread_ms:.0f}ms)"
        )
        return True, None

    def advance_wave(self) -> bool:
        """
        Advance to the next execution wave.

        Returns True if there are more waves, False if complete.
        """
        # First check parallel compliance for current wave
        is_compliant, error = self.check_parallel_compliance()
        if not is_compliant and self.strict:
            raise ParallelExecutionError(error)

        # Clear spawn batch for next wave
        self._spawn_batch = []
        self._current_wave += 1

        has_more = self._current_wave < len(self._waves)
        if has_more:
            next_wave = self.get_current_wave()
            logger.info(
                f"[DelegationEnforcer] Advanced to wave {self._current_wave + 1}: "
                f"{[t.id for t in next_wave]}"
            )
        else:
            logger.info("[DelegationEnforcer] All waves complete")

        return has_more

    def mark_task_completed(self, task_id: str) -> None:
        """Mark a task as completed and check if wave can advance."""
        self.task_graph.mark_completed(task_id)

        # Check if all tasks in current wave are complete
        current_wave = self.get_current_wave()
        all_complete = all(
            self.task_graph.tasks[t.id].status == TaskStatus.COMPLETED for t in current_wave
        )

        if all_complete:
            self.advance_wave()

    def get_enforcement_status(self) -> dict:
        """Get the current enforcement status for debugging/display."""
        current_wave = self.get_current_wave()
        return {
            "current_wave": self._current_wave + 1,
            "total_waves": len(self._waves),
            "current_wave_tasks": [t.id for t in current_wave],
            "spawn_batch": self._spawn_batch,
            "task_statuses": {
                tid: task.status.value for tid, task in self.task_graph.tasks.items()
            },
        }
