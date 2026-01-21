"""
Test for stop_hook.py project root detection logic.
Verifies that the logic correctly identifies the project root containing mcp_bridge.
"""

import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

def resolve_project_root(hooks_dir: Path, env_var: str | None = None) -> Path:
    """
    Reimplementation of the logic in stop_hook.py for testing.
    """
    candidates = []
    
    # 1. Environment variable (High confidence)
    if env_var:
        candidates.append(Path(env_var))
        
    # 2. Current working directory (Common for CLI)
    candidates.append(Path.cwd())
    
    # 3. Relative to hooks dir (For local installation)
    # hooks_dir is usually PROJECT/.claude/hooks
    candidates.append(hooks_dir.parent.parent)
    
    project_root = Path.cwd() # Default
    for candidate in candidates:
        if (candidate / "mcp_bridge").exists():
            project_root = candidate
            break
            
    return project_root

def test_resolve_project_root_via_env_var(tmp_path):
    """Test resolution when CLAUDE_PROJECT_DIR is set correctly."""
    # Setup mock project structure
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    (project_dir / "mcp_bridge").mkdir()
    
    hooks_dir = project_dir / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    
    resolved = resolve_project_root(hooks_dir, env_var=str(project_dir))
    assert resolved == project_dir

def test_resolve_project_root_via_cwd(tmp_path):
    """Test resolution via CWD when env var is missing."""
    project_dir = tmp_path / "current_project"
    project_dir.mkdir()
    (project_dir / "mcp_bridge").mkdir()
    
    hooks_dir = project_dir / ".claude" / "hooks"
    
    # Mock CWD
    with patch.object(Path, 'cwd', return_value=project_dir):
        resolved = resolve_project_root(hooks_dir, env_var=None)
        assert resolved == project_dir

def test_resolve_project_root_via_relative_path(tmp_path):
    """Test resolution via relative path from hooks dir."""
    project_dir = tmp_path / "rel_project"
    project_dir.mkdir()
    (project_dir / "mcp_bridge").mkdir()
    
    hooks_dir = project_dir / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    
    # Mock CWD to be somewhere else (e.g. /tmp)
    with patch.object(Path, 'cwd', return_value=tmp_path):
        resolved = resolve_project_root(hooks_dir, env_var=None)
        assert resolved == project_dir

def test_fallback_logic(tmp_path):
    """Test fallback when mcp_bridge is not found in candidates."""
    # No mcp_bridge anywhere
    hooks_dir = tmp_path / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    
    cwd = tmp_path / "somewhere"
    cwd.mkdir()
    
    with patch.object(Path, 'cwd', return_value=cwd):
        resolved = resolve_project_root(hooks_dir, env_var=None)
        # Should default to CWD
        assert resolved == cwd
