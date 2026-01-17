"""Test suite for todo_delegation.py hook."""

import json
import subprocess
import sys
from pathlib import Path
import pytest

HOOK_PATH = Path(".claude/hooks/todo_delegation.py")

@pytest.fixture
def hook_path():
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found at {HOOK_PATH}")
    return HOOK_PATH

def run_hook(hook_path, input_data):
    """Run the hook script with the given input data."""
    process = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(input_data),
        text=True,
        capture_output=True
    )
    return process

def test_todo_delegation_message_uses_task_tool(hook_path):
    """Verify that the hook message recommends Task() tool, not agent_spawn."""
    input_data = {
        "tool_name": "TodoWrite",
        "tool_input": {
            "todos": [
                {"status": "pending", "description": "Task 1"},
                {"status": "pending", "description": "Task 2"},
            ]
        }
    }

    result = run_hook(hook_path, input_data)

    # It should exit with 1 (warning) or 2 (block) if Stravinsky mode is active
    # We don't control stravinsky mode file existence easily here, but we check stdout.
    
    stdout = result.stdout
    assert "PARALLEL DELEGATION REQUIRED" in stdout
    assert 'Task(subagent_type="explore"' in stdout
    assert "agent_spawn" not in stdout
    
def test_todo_delegation_ignores_single_todo(hook_path):
    """Verify that the hook ignores single pending todo."""
    input_data = {
        "tool_name": "TodoWrite",
        "tool_input": {
            "todos": [
                {"status": "pending", "description": "Task 1"},
            ]
        }
    }

    result = run_hook(hook_path, input_data)
    assert result.returncode == 0
    assert "PARALLEL DELEGATION REQUIRED" not in result.stdout

def test_todo_delegation_ignores_other_tools(hook_path):
    """Verify that the hook ignores tools other than TodoWrite."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {}
    }

    result = run_hook(hook_path, input_data)
    assert result.returncode == 0
    assert result.stdout == ""
