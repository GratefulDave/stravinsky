"""
Tests for parallel execution enforcement.

These tests verify that independent tasks MUST be spawned in parallel,
and sequential execution is blocked.
"""

import pytest
import time
from mcp_bridge.orchestrator.task_graph import (
    TaskGraph,
    Task,
    TaskStatus,
    DelegationEnforcer,
    ParallelExecutionError,
)


class TestTaskGraph:
    """Test TaskGraph dependency tracking."""

    def test_create_task_graph(self):
        """Test creating a task graph from dictionary."""
        data = {
            "research": {"description": "Research codebase", "agent_type": "explore", "depends_on": []},
            "docs": {"description": "Research docs", "agent_type": "dewey", "depends_on": []},
            "implement": {"description": "Implement feature", "agent_type": "frontend", "depends_on": ["research", "docs"]},
        }
        graph = TaskGraph.from_dict(data)

        assert len(graph.tasks) == 3
        assert graph.tasks["research"].dependencies == []
        assert graph.tasks["docs"].dependencies == []
        assert graph.tasks["implement"].dependencies == ["research", "docs"]

    def test_get_ready_tasks(self):
        """Test getting tasks that are ready to execute."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", [])
        graph.add_task("c", "Task C", "frontend", ["a", "b"])

        # Initially, a and b should be ready (no dependencies)
        ready = graph.get_ready_tasks()
        ready_ids = {t.id for t in ready}
        assert ready_ids == {"a", "b"}

        # After marking a complete, b should still be ready, c should not
        graph.mark_completed("a")
        ready = graph.get_ready_tasks()
        ready_ids = {t.id for t in ready}
        assert ready_ids == {"b"}

        # After marking b complete, c should be ready
        graph.mark_completed("b")
        ready = graph.get_ready_tasks()
        ready_ids = {t.id for t in ready}
        assert ready_ids == {"c"}

    def test_get_independent_groups(self):
        """Test grouping tasks into execution waves."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", [])
        graph.add_task("c", "Task C", "frontend", ["a"])
        graph.add_task("d", "Task D", "delphi", ["b"])
        graph.add_task("e", "Task E", "code-reviewer", ["c", "d"])

        waves = graph.get_independent_groups()

        # Wave 1: a, b (no dependencies)
        # Wave 2: c, d (depend on wave 1)
        # Wave 3: e (depends on wave 2)
        assert len(waves) == 3
        assert {t.id for t in waves[0]} == {"a", "b"}
        assert {t.id for t in waves[1]} == {"c", "d"}
        assert {t.id for t in waves[2]} == {"e"}


class TestDelegationEnforcer:
    """Test parallel execution enforcement."""

    def test_enforcer_initialization(self):
        """Test enforcer initializes waves correctly."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", [])

        enforcer = DelegationEnforcer(task_graph=graph)

        current_wave = enforcer.get_current_wave()
        assert len(current_wave) == 2
        assert {t.id for t in current_wave} == {"a", "b"}

    def test_validate_spawn_valid(self):
        """Test validating a valid spawn."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", [])

        enforcer = DelegationEnforcer(task_graph=graph)

        is_valid, error = enforcer.validate_spawn("a")
        assert is_valid
        assert error is None

        is_valid, error = enforcer.validate_spawn("b")
        assert is_valid
        assert error is None

    def test_validate_spawn_invalid_dependency(self):
        """Test that spawning a task with unmet dependencies is blocked."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", ["a"])

        enforcer = DelegationEnforcer(task_graph=graph)

        # Task b depends on a, should be blocked
        is_valid, error = enforcer.validate_spawn("b")
        assert not is_valid
        assert "unmet dependencies" in error.lower()

    def test_record_spawn(self):
        """Test recording spawns."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])

        enforcer = DelegationEnforcer(task_graph=graph)
        enforcer.record_spawn("a", "agent-task-123")

        assert graph.tasks["a"].status == TaskStatus.SPAWNED
        assert graph.tasks["a"].task_id == "agent-task-123"

    def test_parallel_compliance_success(self):
        """Test that parallel spawns within time window pass."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", [])

        enforcer = DelegationEnforcer(task_graph=graph, parallel_window_ms=1000)

        # Spawn both tasks quickly
        enforcer.record_spawn("a", "task-a")
        enforcer.record_spawn("b", "task-b")

        is_compliant, error = enforcer.check_parallel_compliance()
        assert is_compliant
        assert error is None

    def test_parallel_compliance_failure(self):
        """Test that sequential spawns outside time window fail."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", [])

        # Very tight time window (10ms)
        enforcer = DelegationEnforcer(task_graph=graph, parallel_window_ms=10, strict=False)

        # Spawn first task
        enforcer.record_spawn("a", "task-a")

        # Wait longer than the window
        time.sleep(0.05)  # 50ms

        # Spawn second task
        enforcer.record_spawn("b", "task-b")

        is_compliant, error = enforcer.check_parallel_compliance()
        assert not is_compliant
        assert "not spawned in parallel" in error.lower()

    def test_advance_wave(self):
        """Test advancing to next execution wave."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", ["a"])

        enforcer = DelegationEnforcer(task_graph=graph, strict=False)

        # Current wave should be just "a"
        assert {t.id for t in enforcer.get_current_wave()} == {"a"}

        # Spawn and complete a
        enforcer.record_spawn("a", "task-a")
        enforcer.mark_task_completed("a")

        # Should auto-advance to next wave
        assert {t.id for t in enforcer.get_current_wave()} == {"b"}

    def test_strict_mode_raises(self):
        """Test that strict mode raises ParallelExecutionError."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", [])

        # Very tight time window
        enforcer = DelegationEnforcer(task_graph=graph, parallel_window_ms=1, strict=True)

        enforcer.record_spawn("a", "task-a")
        time.sleep(0.01)
        enforcer.record_spawn("b", "task-b")

        with pytest.raises(ParallelExecutionError):
            enforcer.advance_wave()

    def test_get_enforcement_status(self):
        """Test getting enforcement status for debugging."""
        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])
        graph.add_task("b", "Task B", "dewey", [])

        enforcer = DelegationEnforcer(task_graph=graph)
        enforcer.record_spawn("a", "task-a")

        status = enforcer.get_enforcement_status()

        assert status["current_wave"] == 1
        assert status["total_waves"] == 1
        assert "a" in status["current_wave_tasks"]
        assert "b" in status["current_wave_tasks"]
        assert status["task_statuses"]["a"] == "spawned"
        assert status["task_statuses"]["b"] == "pending"


class TestEnforcerIntegration:
    """Test enforcer integration with agent_spawn."""

    def test_set_and_get_enforcer(self):
        """Test setting and getting the global enforcer."""
        from mcp_bridge.tools.agent_manager import (
            set_delegation_enforcer,
            get_delegation_enforcer,
            clear_delegation_enforcer,
        )

        graph = TaskGraph()
        graph.add_task("a", "Task A", "explore", [])

        enforcer = DelegationEnforcer(task_graph=graph)
        set_delegation_enforcer(enforcer)

        assert get_delegation_enforcer() is enforcer

        clear_delegation_enforcer()
        assert get_delegation_enforcer() is None
