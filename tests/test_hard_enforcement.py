"""Tests for Hard Parallel Enforcement hooks."""

import json
import os
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp_bridge.hooks.post_tool.parallel_validation import process_hook as post_process
from mcp_bridge.hooks.pre_tool.agent_spawn_validator import process_hook as pre_process

class TestParallelValidation:
    """Tests for post_tool/parallel_validation.py logic."""

    @pytest.fixture
    def mock_cwd(self, tmp_path):
        """Mock CLAUDE_CWD to point to a temp dir."""
        state_file = tmp_path / ".claude/parallel_state.json"
        with patch("mcp_bridge.hooks.post_tool.parallel_validation.get_state_file", return_value=state_file):
            yield state_file

    def test_tracks_pending_tasks(self, mock_cwd):
        """Verify it counts pending tasks and sets flag."""
        hook_input = {
            "tool_name": "TodoWrite",
            "tool_input": {
                "todos": [
                    {"status": "pending", "content": "Task 1"},
                    {"status": "pending", "content": "Task 2"},
                    {"status": "completed", "content": "Task 0"}
                ]
            }
        }
        
        post_process(hook_input)
        
        assert mock_cwd.exists()
        state = json.loads(mock_cwd.read_text())
        assert state["delegation_required"] is True
        assert state["pending_count"] == 2

    def test_ignore_single_task(self, mock_cwd):
        """Verify it ignores single pending task."""
        hook_input = {
            "tool_name": "TodoWrite",
            "tool_input": {
                "todos": [
                    {"status": "pending", "content": "Task 1"}
                ]
            }
        }
        
        post_process(hook_input)
        
        assert not mock_cwd.exists()

    def test_clears_flag_on_delegation(self, mock_cwd):
        """Verify Task/agent_spawn clears the flag."""
        mock_cwd.parent.mkdir(parents=True, exist_ok=True)
        mock_cwd.write_text(json.dumps({"delegation_required": True}))
        
        hook_input = {
            "tool_name": "Task",
            "tool_input": {}
        }
        
        post_process(hook_input)
        
        state = json.loads(mock_cwd.read_text())
        assert state["delegation_required"] is False

    def test_session_isolation(self, tmp_path):
        """Verify different sessions use different state files."""
        # Unpatch get_state_file to test the logic (only patch sys/os if needed, but we used os.environ)
        
        # We need to reload the module to unpatch or just import the function and test logic directly
        from mcp_bridge.hooks.post_tool.parallel_validation import get_state_file
        
        with patch.dict(os.environ, {"CLAUDE_CWD": str(tmp_path), "CLAUDE_SESSION_ID": "session1"}):
            path1 = get_state_file()
            assert path1.name == "parallel_state_session1.json"
            
        with patch.dict(os.environ, {"CLAUDE_CWD": str(tmp_path), "CLAUDE_SESSION_ID": "session2"}):
            path2 = get_state_file()
            assert path2.name == "parallel_state_session2.json"
            
        assert path1 != path2


class TestAgentSpawnValidator:
    """Tests for pre_tool/agent_spawn_validator.py logic."""

    @pytest.fixture
    def mock_env(self, tmp_path):
        state_file = tmp_path / ".claude/parallel_state.json"
        config_file = tmp_path / ".stravinsky/config.json"
        
        # Patch get_state_file and get_project_dir
        with patch("mcp_bridge.hooks.pre_tool.agent_spawn_validator.get_state_file", return_value=state_file), \
             patch("mcp_bridge.hooks.pre_tool.agent_spawn_validator.get_project_dir", return_value=tmp_path):
            yield state_file, config_file

    def test_blocks_direct_tools_when_required(self, mock_env):
        """Verify it returns exit code 2 when delegation required."""
        state_file, config_file = mock_env
        
        # Setup state
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"delegation_required": True}))
        
        # Setup config (enforce=True)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps({"enforce_parallel_delegation": True}))
        
        hook_input = {"toolName": "Read"}
        exit_code = pre_process(hook_input)
        assert exit_code == 2

    def test_allows_task_tool(self, mock_env):
        """Verify it allows Task tool even when delegation required."""
        state_file, config_file = mock_env
        
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"delegation_required": True}))
        
        hook_input = {"toolName": "Task"}
        exit_code = pre_process(hook_input)
        assert exit_code == 0

    def test_allows_agent_spawn(self, mock_env):
        """Verify it allows agent_spawn tool."""
        state_file, config_file = mock_env
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"delegation_required": True}))
        
        hook_input = {"toolName": "agent_spawn"}
        exit_code = pre_process(hook_input)
        assert exit_code == 0

    def test_allows_if_not_enforced(self, mock_env):
        """Verify it allows if enforcement is disabled."""
        state_file, config_file = mock_env
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"delegation_required": True}))
        
        # Config missing or false
        
        hook_input = {"toolName": "Read"}
        exit_code = pre_process(hook_input)
        assert exit_code == 0

    def test_allows_if_env_var_override(self, mock_env):
        """Verify environment variable override."""
        state_file, config_file = mock_env
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"delegation_required": True}))
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps({"enforce_parallel_delegation": True}))
        
        with patch.dict(os.environ, {"STRAVINSKY_ALLOW_SEQUENTIAL": "true"}):
            hook_input = {"toolName": "Read"}
            exit_code = pre_process(hook_input)
            assert exit_code == 0
