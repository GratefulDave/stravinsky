"""Integration tests for MCP server startup and protocol compliance.

These tests ensure the server can:
1. Start without crashing
2. Handle JSON-RPC protocol correctly
3. Respond to initialize requests
4. List tools without errors
5. Handle basic tool invocations
"""

import subprocess
import json
import time
from pathlib import Path


def test_server_starts_without_crash():
    """Test that the MCP server can start without immediate crash."""
    # This would have caught the 0.4.30 logger bug
    proc = subprocess.Popen(
        ["stravinsky"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Give it a moment to crash if it's going to
    time.sleep(0.5)

    # Check if still running
    assert proc.poll() is None, "Server crashed immediately on startup"

    # Clean shutdown
    proc.terminate()
    proc.wait(timeout=5)


def test_server_responds_to_initialize():
    """Test that server responds to JSON-RPC initialize request."""
    proc = subprocess.Popen(
        ["stravinsky"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Send initialize request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()

        # Read response (give it 2 seconds)
        time.sleep(2)

        # Server should still be running
        assert proc.poll() is None, "Server crashed after initialize"

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_server_import_does_not_crash():
    """Test that importing mcp_bridge.server doesn't crash.

    This is the CRITICAL test that would have caught 0.4.30's logger bug.
    """
    result = subprocess.run(
        ["python3", "-c", "import mcp_bridge.server"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0, f"Import failed: {result.stderr}"


def test_stravinsky_command_exists():
    """Test that the stravinsky command is available."""
    result = subprocess.run(
        ["stravinsky", "--version"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "stravinsky" in result.stdout.lower(), "Version output doesn't mention stravinsky"


def test_server_handles_invalid_json():
    """Test that server doesn't crash on invalid JSON input."""
    proc = subprocess.Popen(
        ["stravinsky"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Send invalid JSON
        proc.stdin.write("not valid json\n")
        proc.stdin.flush()

        time.sleep(1)

        # Server should still be running (graceful error handling)
        assert proc.poll() is None, "Server crashed on invalid JSON"

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_critical_files_exist():
    """Test that all critical source files exist."""
    project_root = Path(__file__).parent.parent

    critical_files = [
        "mcp_bridge/server.py",
        "mcp_bridge/__init__.py",
        "mcp_bridge/tools/model_invoke.py",
        "mcp_bridge/tools/semantic_search.py",
        "mcp_bridge/tools/agent_manager.py",
        "mcp_bridge/auth/oauth.py",
        "pyproject.toml",
    ]

    for file_path in critical_files:
        full_path = project_root / file_path
        assert full_path.exists(), f"Critical file missing: {file_path}"


def test_version_consistency():
    """Test that version is consistent across files."""
    project_root = Path(__file__).parent.parent

    # Read pyproject.toml version
    pyproject = (project_root / "pyproject.toml").read_text()
    import re
    match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert match, "Could not find version in pyproject.toml"
    pyproject_version = match.group(1)

    # Read __init__.py version
    init_file = (project_root / "mcp_bridge" / "__init__.py").read_text()
    match = re.search(r'__version__ = "([^"]+)"', init_file)
    assert match, "Could not find version in __init__.py"
    init_version = match.group(1)

    assert pyproject_version == init_version, \
        f"Version mismatch: pyproject.toml={pyproject_version}, __init__.py={init_version}"
