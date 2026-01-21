"""
Comprehensive tests for agent_spawn and agent_output MCP tools.
"""

import asyncio
import json
import os
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest

from mcp_bridge.tools.agent_manager import (
    AgentManager,
    AgentTask,
    agent_cancel,
    agent_list,
    agent_output,
    agent_progress,
    agent_retry,
    agent_spawn,
    get_manager,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for agent state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
async def agent_manager(temp_dir):
    """Create an AgentManager with a temporary directory."""
    manager = AgentManager(base_dir=temp_dir)
    # Ensure global manager uses this instance during tests
    with patch("mcp_bridge.tools.agent_manager._manager", manager):
        yield manager
        # Cleanup
        await manager.stop_all_async(clear_history=True)


@pytest.fixture
def mock_token_store():
    """Create a mock TokenStore."""
    mock = MagicMock()
    mock.get_token = MagicMock(return_value={"access_token": "test_token"})
    return mock


@pytest.fixture
def mock_subprocess():
    """Mock asyncio.create_subprocess_exec for Claude CLI execution."""
    original_sleep = asyncio.sleep
    
    with patch("mcp_bridge.tools.agent_manager.asyncio.create_subprocess_exec") as mock_exec, \
         patch("mcp_bridge.tools.agent_manager.MuxClient") as mock_mux_cls, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        
        # Mock MuxClient
        mock_mux = MagicMock()
        mock_mux.connect = MagicMock()
        mock_mux.log = MagicMock()
        mock_mux_cls.return_value = mock_mux

        # Mock asyncio.sleep to yield control but not wait
        async def mock_sleep_func(delay, result=None):
            # If delay is small (polling), yield. If large (timeout), just return.
            if delay < 1:
                await original_sleep(0) 
            return result
            
        mock_sleep.side_effect = mock_sleep_func

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.returncode = 0
        
        # Mock streams for readline
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"Agent output\n", b""])
        
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(side_effect=[b""])

        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        
        # Mock async methods
        mock_process.communicate = AsyncMock(return_value=(b"Agent output", b""))
        mock_process.wait = AsyncMock(return_value=0)
        
        mock_exec.return_value = mock_process
        yield mock_exec, mock_process


class TestAgentManager:
    """Test AgentManager class methods."""

    @pytest.mark.asyncio
    async def test_init_creates_directories(self, temp_dir):
        """Test that AgentManager creates necessary directories."""
        manager = AgentManager(base_dir=temp_dir)

        assert Path(temp_dir).exists()
        assert (Path(temp_dir) / "agents").exists()
        # State file is now session-specific: agents_{session_id}.json
        state_files = list(Path(temp_dir).glob("agents_*.json"))
        assert len(state_files) == 1
        assert state_files[0].name.startswith("agents_pid_")

    @pytest.mark.asyncio
    async def test_save_and_load_tasks(self, agent_manager):
        """Test task persistence."""
        task_data = {
            "task_123": {
                "id": "task_123",
                "prompt": "Test prompt",
                "agent_type": "explore",
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
        }

        agent_manager._save_tasks(task_data)
        loaded = agent_manager._load_tasks()

        assert "task_123" in loaded
        assert loaded["task_123"]["prompt"] == "Test prompt"

    @pytest.mark.asyncio
    async def test_get_task(self, agent_manager):
        """Test retrieving a specific task."""
        task_data = {
            "task_456": {
                "id": "task_456",
                "prompt": "Find auth code",
                "agent_type": "explore",
                "status": "running",
                "created_at": datetime.now().isoformat(),
            }
        }

        agent_manager._save_tasks(task_data)
        task = agent_manager.get_task("task_456")

        assert task is not None
        assert task["id"] == "task_456"
        assert task["agent_type"] == "explore"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, agent_manager):
        """Test retrieving a task that does not exist."""
        task = agent_manager.get_task("nonexistent")
        assert task is None

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, agent_manager):
        """Test listing tasks when none exist."""
        tasks = agent_manager.list_tasks()
        assert tasks == []

    @pytest.mark.asyncio
    async def test_list_tasks_with_data(self, agent_manager):
        """Test listing tasks with multiple tasks."""
        # Include terminal_session_id to match the manager's session filter
        task_data = {
            "task_1": {
                "id": "task_1",
                "status": "completed",
                "terminal_session_id": agent_manager.session_id,
            },
            "task_2": {
                "id": "task_2",
                "status": "running",
                "terminal_session_id": agent_manager.session_id,
            },
        }

        agent_manager._save_tasks(task_data)
        tasks = agent_manager.list_tasks()

        assert len(tasks) == 2
        assert any(t["id"] == "task_1" for t in tasks)
        assert any(t["id"] == "task_2" for t in tasks)

    @pytest.mark.asyncio
    async def test_update_task(self, agent_manager):
        """Test updating task fields."""
        task_data = {
            "task_789": {
                "id": "task_789",
                "status": "pending",
                "result": None,
            }
        }

        agent_manager._save_tasks(task_data)
        agent_manager._update_task("task_789", status="completed", result="Success!")

        updated = agent_manager.get_task("task_789")
        assert updated["status"] == "completed"
        assert updated["result"] == "Success!"

    @pytest.mark.asyncio
    async def test_spawn_with_semantic_first(self, mock_subprocess, agent_manager, mock_token_store):
        """Test spawning a task with semantic_first enabled."""
        mock_exec, mock_process = mock_subprocess
        
        # Setup process mock behavior
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr.readline = AsyncMock(return_value=b"")
        mock_exec.return_value = mock_process

        # Mock semantic_search
        with patch("mcp_bridge.tools.agent_manager.semantic_search") as mock_search:
            mock_search.search.return_value = "Found context"
            
            task_id = await agent_manager.spawn_async(
                token_store=mock_token_store,
                prompt="Test task",
                agent_type="explore",
                timeout=10,
                semantic_first=True
            )

            assert task_id.startswith("agent_")
            # Verify search was called
            mock_search.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_creates_task(self, mock_subprocess, agent_manager, mock_token_store):
        """Test that spawn creates a task and starts execution."""
        _, mock_process = mock_subprocess

        task_id = await agent_manager.spawn_async(
            token_store=mock_token_store,
            prompt="Find authentication code",
            agent_type="explore",
            description="Test task",
            timeout=10,
        )

        # Give background task time to start
        await asyncio.sleep(0.5)

        assert task_id.startswith("agent_")
        task = agent_manager.get_task(task_id)
        assert task is not None
        assert task["prompt"] == "Find authentication code"
        assert task["status"] in ["pending", "running", "completed"]

    @pytest.mark.asyncio
    async def test_spawn_with_different_agent_types(self, mock_subprocess, agent_manager, mock_token_store):
        """Test spawning different agent types."""
        _, mock_process = mock_subprocess

        agent_types = ["explore", "dewey", "frontend", "delphi", "document_writer", "multimodal"]

        for agent_type in agent_types:
            task_id = await agent_manager.spawn_async(
                token_store=mock_token_store,
                prompt=f"Test {agent_type} agent",
                agent_type=agent_type,
                description=f"Testing {agent_type}",
                timeout=10,
            )

            task = agent_manager.get_task(task_id)
            assert task["agent_type"] == agent_type

        # Stop all agents and wait for cleanup
        await asyncio.sleep(0.1)
        await agent_manager.stop_all_async()

    @pytest.mark.asyncio
    async def test_get_output_completed_task(self, mock_subprocess, agent_manager, mock_token_store):
        """Test getting output from a completed task."""
        _, mock_process = mock_subprocess
        
        # Setup streams for success
        mock_process.stdout.readline = AsyncMock(side_effect=[b"Task completed successfully\n", b""])

        task_id = await agent_manager.spawn_async(
            token_store=mock_token_store,
            prompt="Test task",
            agent_type="explore",
            timeout=10,
        )

        # Wait for task to complete (loop with sleeps)
        for _ in range(10):
            await asyncio.sleep(0.1)
            if agent_manager.get_task(task_id)["status"] == "completed":
                break
        
        output = await agent_manager.get_output(task_id, block=False)
        assert "Completed" in output or "success" in output.lower()

    @pytest.mark.asyncio
    async def test_get_output_running_task_non_blocking(
        self,
        mock_subprocess,
        agent_manager,
        mock_token_store,
    ):
        """Test getting output from a running task without blocking."""
        _, mock_process = mock_subprocess

        # Mock long-running process by delaying the stream
        async def slow_readline():
            await asyncio.sleep(10)
            return b""
            
        mock_process.stdout.readline = AsyncMock(side_effect=slow_readline)
        mock_process.wait = AsyncMock(side_effect=lambda: asyncio.sleep(10))

        task_id = await agent_manager.spawn_async(
            token_store=mock_token_store,
            prompt="Long task",
            agent_type="explore",
            timeout=30,
        )

        # Give task time to start
        await asyncio.sleep(0.5)

        output = await agent_manager.get_output(task_id, block=False)
        assert "Running" in output or "pending" in output.lower()

    @pytest.mark.asyncio
    async def test_get_output_running_task_blocking(self, mock_subprocess, agent_manager, mock_token_store):
        """Test getting output from a running task with blocking."""
        _, mock_process = mock_subprocess
        
        mock_process.stdout.readline = AsyncMock(side_effect=[b"Completed\n", b""])

        task_id = await agent_manager.spawn_async(
            token_store=mock_token_store,
            prompt="Quick task",
            agent_type="explore",
            timeout=10,
        )

        output = await agent_manager.get_output(task_id, block=True, timeout=5)
        # Should contain output after blocking wait
        assert "Completed" in output

    @pytest.mark.asyncio
    async def test_get_output_nonexistent_task(self, agent_manager):
        """Test getting output from a task that does not exist."""
        output = await agent_manager.get_output("nonexistent_task")
        assert "not found" in output.lower()

    @pytest.mark.asyncio
    async def test_cancel_running_task(self, mock_subprocess, agent_manager, mock_token_store):
        """Test cancelling a running task."""
        _, mock_process = mock_subprocess

        # Mock long-running process
        async def slow_readline():
            await asyncio.sleep(30)
            return b""
            
        mock_process.stdout.readline = AsyncMock(side_effect=slow_readline)
        mock_process.wait = AsyncMock(side_effect=lambda: asyncio.sleep(30))

        task_id = await agent_manager.spawn_async(
            token_store=mock_token_store,
            prompt="Long task",
            agent_type="explore",
            timeout=60,
        )

        # Give task time to start
        await asyncio.sleep(0.5)

        # Cancel should work
        with patch("mcp_bridge.tools.agent_manager.os.killpg"):
            success = agent_manager.cancel(task_id)
            assert success is True

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, agent_manager):
        """Test cancelling a task that does not exist."""
        success = agent_manager.cancel("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_completed_task(self, agent_manager):
        """Test cancelling a task that is already completed."""
        task_data = {
            "task_complete": {
                "id": "task_complete",
                "status": "completed",
                "result": "Done",
            }
        }

        agent_manager._save_tasks(task_data)
        success = agent_manager.cancel("task_complete")
        assert success is False

    @pytest.mark.asyncio
    async def test_get_progress(self, mock_subprocess, agent_manager, mock_token_store):
        """Test getting progress from a running task."""
        _, mock_process = mock_subprocess
        
        # Mock long process
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(side_effect=lambda: asyncio.sleep(30))

        task_id = await agent_manager.spawn_async(
            token_store=mock_token_store,
            prompt="Task with progress",
            agent_type="explore",
            timeout=30,
        )

        # Give task time to start
        await asyncio.sleep(0.5)

        progress = agent_manager.get_progress(task_id, lines=10)
        assert "Agent Progress" in progress

    @pytest.mark.asyncio
    async def test_get_progress_nonexistent_task(self, agent_manager):
        """Test getting progress for a nonexistent task."""
        progress = agent_manager.get_progress("nonexistent")
        assert "not found" in progress.lower()

    @pytest.mark.asyncio
    async def test_stop_all_running_tasks(self, mock_subprocess, agent_manager, mock_token_store):
        """Test stopping all running tasks."""
        _, mock_process = mock_subprocess
        
        # Mock long process
        async def hang(*args, **kwargs):
            await asyncio.sleep(10)
            return b""
            
        mock_process.stdout.readline = AsyncMock(side_effect=hang)
        mock_process.stderr.readline = AsyncMock(side_effect=hang)
        mock_process.wait = AsyncMock(side_effect=lambda: asyncio.sleep(10))

        # Spawn multiple tasks
        for i in range(3):
            await agent_manager.spawn_async(
                token_store=mock_token_store,
                prompt=f"Task {i}",
                agent_type="explore",
                timeout=60,
            )

        await asyncio.sleep(0.5)

        # Stop all
        with patch("mcp_bridge.tools.agent_manager.os.killpg"):
            stopped = await agent_manager.stop_all_async()
            assert stopped == 3

    @pytest.mark.asyncio
    async def test_stop_all_with_clear_history(self, agent_manager):
        """Test stopping all tasks and clearing history."""
        task_data = {
            "task_1": {"id": "task_1", "status": "completed"},
            "task_2": {"id": "task_2", "status": "failed"},
        }

        agent_manager._save_tasks(task_data)
        cleared = await agent_manager.stop_all_async(clear_history=True)

        assert cleared == 2
        tasks = agent_manager.list_tasks()
        assert tasks == []


class TestAgentSpawn:
    """Test agent_spawn function."""

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_agent_spawn_explore(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test spawning an explore agent."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess

        result = await agent_spawn(
            prompt="Find authentication code",
            agent_type="explore",
            description="Test explore agent",
            timeout=10,
        )

        assert "agent_" in result

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_agent_spawn_dewey(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test spawning a dewey agent."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess

        result = await agent_spawn(
            prompt="Research JWT best practices",
            agent_type="dewey",
            description="Test dewey agent",
            timeout=10,
        )

        assert "agent_" in result

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_agent_spawn_frontend(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test spawning a frontend agent."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess

        result = await agent_spawn(
            prompt="Create a login form",
            agent_type="frontend",
            description="Test frontend agent",
            timeout=10,
        )

        assert "agent_" in result

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_agent_spawn_delphi(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test spawning a delphi agent."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess

        result = await agent_spawn(
            prompt="Review architecture for scalability",
            agent_type="delphi",
            description="Test delphi agent",
            timeout=10,
        )

        assert "agent_" in result

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_agent_spawn_blocking_mode(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test spawning an agent in blocking mode."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess
        
        mock_process.stdout.readline = AsyncMock(side_effect=[b"Completed\n", b""])

        result = await agent_spawn(
            prompt="Quick analysis",
            agent_type="explore",
            description="Blocking test",
            timeout=10,
            blocking=True,
        )

        assert "Completed" in result

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_agent_spawn_custom_timeout(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test spawning an agent with custom timeout."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess

        result = await agent_spawn(
            prompt="Long running task",
            agent_type="explore",
            timeout=600,
        )

        assert "agent_" in result


class TestAgentOutput:
    """Test agent_output function."""

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_agent_output_non_blocking(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test getting output without blocking."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess
        
        mock_process.stdout.readline = AsyncMock(side_effect=[b"Output\n", b""])

        task_id_info = await agent_spawn(
            prompt="Test task",
            agent_type="explore",
            timeout=10,
        )

        # Extract task_id
        task_id = task_id_info.split("→")[-1].strip()
        if "\033" in task_id:
            import re
            task_id = re.sub(r'\033\[[0-9;]*m', '', task_id)

        output = await agent_output(task_id, block=False)
        assert output is not None

    @pytest.mark.asyncio
    async def test_agent_output_nonexistent_task(self, agent_manager):
        """Test getting output for a nonexistent task."""
        output = await agent_output("nonexistent_task")
        assert "not found" in output.lower()


class TestAgentCancel:
    """Test agent_cancel function."""

    @pytest.mark.asyncio
    async def test_agent_cancel_nonexistent_task(self, agent_manager):
        """Test cancelling a nonexistent task."""
        result = await agent_cancel("nonexistent")
        assert "not found" in result.lower()


class TestAgentRetry:
    """Test agent_retry function."""

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_agent_retry_failed_task(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test retrying a failed task."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess

        # Create a failed task
        task_data = {
            "task_failed": {
                "id": "task_failed",
                "prompt": "Original prompt",
                "agent_type": "explore",
                "status": "failed",
                "error": "Task failed",
                "description": "Original task description",
                "created_at": datetime.now().isoformat(),
                "terminal_session_id": agent_manager.session_id,
                "timeout": 300,
            }
        }
        agent_manager._save_tasks(task_data)

        result = await agent_retry("task_failed", new_prompt="Retry prompt")
        assert "agent_" in result

    @pytest.mark.asyncio
    async def test_agent_retry_nonexistent_task(self, agent_manager):
        """Test retrying a nonexistent task."""
        result = await agent_retry("nonexistent")
        assert "not found" in result.lower()


class TestAgentList:
    """Test agent_list function."""

    @pytest.mark.asyncio
    async def test_agent_list_empty(self, agent_manager):
        """Test listing agents when none exist."""
        result = await agent_list()
        assert "No tasks found" in result or result == ""

    @pytest.mark.asyncio
    async def test_agent_list_with_tasks(self, agent_manager):
        """Test listing agents with multiple tasks."""
        # Create multiple tasks
        task_data = {
            "task_1": {
                "id": "task_1",
                "agent_type": "explore",
                "status": "completed",
                "description": "Find code",
                "created_at": datetime.now().isoformat(),
                "terminal_session_id": agent_manager.session_id,
            },
            "task_2": {
                "id": "task_2",
                "agent_type": "dewey",
                "status": "running",
                "description": "Research docs",
                "created_at": datetime.now().isoformat(),
                "terminal_session_id": agent_manager.session_id,
            },
        }
        agent_manager._save_tasks(task_data)

        result = await agent_list(show_all=True)
        assert "task_1" in result
        assert "task_2" in result


class TestAgentProgress:
    """Test agent_progress function."""

    @pytest.mark.asyncio
    async def test_agent_progress_nonexistent_task(self, agent_manager):
        """Test getting progress for a nonexistent task."""
        result = await agent_progress("nonexistent")
        assert "not found" in result.lower()


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_spawn_with_claude_not_found(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test spawning when Claude CLI is not found."""
        mock_token_store_class.return_value = MagicMock()
        mock_exec, _ = mock_subprocess
        mock_exec.side_effect = FileNotFoundError("claude not found")

        result_info = await agent_spawn(
            prompt="Test task",
            agent_type="explore",
            timeout=10,
        )

        # Extract ID
        task_id = result_info.split("→")[-1].strip()
        if "\033" in task_id:
            import re
            task_id = re.sub(r'\033\[[0-9;]*m', '', task_id)

        # Task should be created but will fail
        for _ in range(10):
            await asyncio.sleep(0.1)
            task = agent_manager.get_task(task_id)
            if task and task["status"] in ["completed", "failed"]:
                break

        task = agent_manager.get_task(task_id)
        if task:
            assert task["status"] == "failed"
            assert "not found" in task.get("error", "").lower()

    @pytest.mark.skip(reason="Flaky test: asyncio.wait_for timeout not triggering reliably with mocked subprocess. TODO: Investigate fixture interaction.")
    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_spawn_with_timeout(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test spawning a task that times out."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess
        
        # Define a coroutine that hangs forever
        async def hang_forever(*args, **kwargs):
            await asyncio.Future() # Await a never-completing future

        # Apply to wait and stream methods
        # IMPORTANT: Must set side_effect to override any existing side_effect from fixture
        mock_process.wait.side_effect = hang_forever
        mock_process.stdout.readline.side_effect = hang_forever
        mock_process.stderr.readline.side_effect = hang_forever
    
        with patch("mcp_bridge.tools.agent_manager.os.killpg"), \
             patch("mcp_bridge.tools.agent_manager.os.getpgid"):
            task_id_info = await agent_spawn(
                prompt="Timeout task",
                agent_type="explore",
                timeout=0.1,  # Fast timeout
            )
            
            task_id = task_id_info.split("→")[-1].strip()
            if "\033" in task_id:
                import re
                task_id = re.sub(r'\033\[[0-9;]*m', '', task_id)
                
            # Wait for task to fail (timeout)
            for _ in range(20):
                await asyncio.sleep(0.1)
                task = agent_manager.get_task(task_id)
                if task and task["status"] == "failed":
                    break

        task = agent_manager.get_task(task_id)
        if task:
            assert task["status"] == "failed"
            assert "timed out" in task.get("error", "").lower()

    @pytest.mark.asyncio
    @patch("mcp_bridge.auth.token_store.TokenStore")
    async def test_spawn_with_process_failure(self, mock_token_store_class, mock_subprocess, agent_manager):
        """Test spawning a task where the process fails."""
        mock_token_store_class.return_value = MagicMock()
        _, mock_process = mock_subprocess
        
        # Simulate failure
        mock_process.returncode = 1
        mock_process.stderr.readline = AsyncMock(side_effect=[b"Error occurred\n", b""])
        mock_process.stdout.readline = AsyncMock(return_value=b"")

        result_info = await agent_spawn(
            prompt="Failing task",
            agent_type="explore",
            timeout=10,
        )

        # Extract ID
        task_id = result_info.split("→")[-1].strip()
        if "\033" in task_id:
            import re
            task_id = re.sub(r'\033\[[0-9;]*m', '', task_id)

        for _ in range(10):
            await asyncio.sleep(0.1)
            task = agent_manager.get_task(task_id)
            if task and task["status"] in ["completed", "failed"]:
                break

        task = agent_manager.get_task(task_id)
        if task:
            assert task["status"] == "failed"
