"""Test suite for Phase 1: Smart Semantic Search Auto-Index.

Tests cover:
- Index existence check before semantic_search
- Interactive Y/N prompt workflow
- Auto-start file watcher when index exists
- Timeout handling for non-interactive environments
- File watcher lifecycle (create, verify, cleanup)
"""

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, call
import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_project():
    """Create temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        # Create sample files
        (project_path / "src").mkdir()
        (project_path / "src" / "auth.py").write_text(
            "def authenticate(user):\n    return True"
        )
        yield str(project_path)


@pytest.fixture
def mock_store():
    """Mock CodebaseVectorStore."""
    store = MagicMock()
    store.collection = MagicMock()
    store.collection.count.return_value = 0  # No index by default
    return store


@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider."""
    provider = AsyncMock()
    provider.dimension = 768
    provider.name = "mock"
    provider.check_available.return_value = True
    provider.get_embedding.return_value = [0.1] * 768
    return provider


# ============================================================================
# TEST: Index Existence Check
# ============================================================================


@pytest.mark.asyncio
async def test_check_index_exists_empty(mock_store):
    """Test _check_index_exists returns False when no documents."""
    from mcp_bridge.tools.semantic_search import _check_index_exists

    mock_store.collection.count.return_value = 0
    assert _check_index_exists(mock_store) is False


@pytest.mark.asyncio
async def test_check_index_exists_populated(mock_store):
    """Test _check_index_exists returns True when documents exist."""
    from mcp_bridge.tools.semantic_search import _check_index_exists

    mock_store.collection.count.return_value = 42
    assert _check_index_exists(mock_store) is True


@pytest.mark.asyncio
async def test_check_index_exists_error_handling(mock_store):
    """Test _check_index_exists handles errors gracefully."""
    from mcp_bridge.tools.semantic_search import _check_index_exists

    mock_store.collection.count.side_effect = RuntimeError("DB connection lost")
    assert _check_index_exists(mock_store) is False


# ============================================================================
# TEST: Interactive Y/N Prompt
# ============================================================================


@pytest.mark.asyncio
async def test_prompt_yes_creates_index(temp_project, mock_store):
    """Test Y response triggers index creation and watcher start."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.semantic_index") as mock_index, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher") as mock_watcher, \
         patch("builtins.input", return_value="y"):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index

        from mcp_bridge.tools.semantic_search import semantic_search

        # This should trigger the prompt and create index
        result = await semantic_search("find auth", project_path=temp_project)

        # Verify index was created
        mock_index.assert_called_once_with(temp_project, "ollama")

        # Verify watcher was started
        mock_watcher.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_no_returns_error(temp_project, mock_store):
    """Test N response returns helpful error message."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("builtins.input", return_value="n"):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index

        from mcp_bridge.tools.semantic_search import semantic_search

        result = await semantic_search("find auth", project_path=temp_project)

        # Verify error message with instructions
        assert "Index required" in result or "semantic_index" in result


@pytest.mark.asyncio
async def test_prompt_empty_defaults_to_yes(temp_project, mock_store):
    """Test empty response defaults to Y (create index)."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.semantic_index") as mock_index, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher") as mock_watcher, \
         patch("builtins.input", return_value=""):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        # Empty should trigger index creation (default=Yes)
        mock_index.assert_called_once()


# ============================================================================
# TEST: Timeout Handling
# ============================================================================


@pytest.mark.asyncio
async def test_non_interactive_skips_prompt(temp_project, mock_store, monkeypatch):
    """Test non-interactive environment (no TTY) skips prompt."""
    # Mock stdin.isatty() to return False
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store:
        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index

        from mcp_bridge.tools.semantic_search import semantic_search

        result = await semantic_search("find auth", project_path=temp_project)

        # Should return error without prompting
        assert "Index required" in result or "semantic_index" in result


@pytest.mark.asyncio
async def test_prompt_timeout_returns_no(temp_project, mock_store):
    """Test timeout during prompt defaults to N."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search._prompt_with_timeout") as mock_prompt:

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index
        mock_prompt.side_effect = TimeoutError("30s timeout")

        from mcp_bridge.tools.semantic_search import semantic_search

        result = await semantic_search("find auth", project_path=temp_project)

        # Timeout should return error message
        assert "Index required" in result or "semantic_index" in result


@pytest.mark.asyncio
async def test_prompt_eoferror_returns_no(temp_project, mock_store):
    """Test EOFError during prompt (stdin closed) defaults to N."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("builtins.input", side_effect=EOFError()):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index

        from mcp_bridge.tools.semantic_search import semantic_search

        result = await semantic_search("find auth", project_path=temp_project)

        # EOFError should return error message
        assert "Index required" in result or "semantic_index" in result


# ============================================================================
# TEST: Auto-Start File Watcher
# ============================================================================


@pytest.mark.asyncio
async def test_watcher_starts_when_index_exists(temp_project, mock_store):
    """Test file watcher auto-starts after successful search when index exists."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher") as mock_watcher, \
         patch("mcp_bridge.tools.semantic_search.get_file_watcher", return_value=None):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 100  # Index exists
        mock_store.search.return_value = []  # Mock search results

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        # Watcher should start after successful search
        mock_watcher.assert_called_once_with(
            temp_project,
            "ollama",
            debounce_seconds=2.0
        )


@pytest.mark.asyncio
async def test_watcher_not_started_if_already_running(temp_project, mock_store):
    """Test file watcher is NOT started if already running."""
    existing_watcher = MagicMock()

    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher") as mock_watcher, \
         patch("mcp_bridge.tools.semantic_search.get_file_watcher", return_value=existing_watcher):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 100  # Index exists
        mock_store.search.return_value = []

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        # Watcher should NOT be started (already running)
        mock_watcher.assert_not_called()


# ============================================================================
# TEST: File Watcher Lifecycle
# ============================================================================


@pytest.mark.asyncio
async def test_watcher_cleanup_on_exit(temp_project):
    """Test file watchers are cleaned up on process exit."""
    with patch("mcp_bridge.tools.semantic_search.stop_file_watcher") as mock_stop, \
         patch("mcp_bridge.tools.semantic_search.list_file_watchers") as mock_list:

        # Mock active watchers
        mock_list.return_value = [
            {"project_path": temp_project, "provider": "ollama"},
        ]

        from mcp_bridge.tools.semantic_search import _cleanup_all_watchers

        _cleanup_all_watchers()

        # Verify stop was called for each watcher
        mock_stop.assert_called_once_with(temp_project)


@pytest.mark.asyncio
async def test_cleanup_registered_only_once(temp_project):
    """Test cleanup is registered with atexit only once."""
    with patch("atexit.register") as mock_atexit:
        from mcp_bridge.tools.semantic_search import _register_cleanup_once

        # Call multiple times
        _register_cleanup_once()
        _register_cleanup_once()
        _register_cleanup_once()

        # Should only register once
        assert mock_atexit.call_count == 1


@pytest.mark.asyncio
async def test_watcher_survives_restart(temp_project, mock_store):
    """Test file watcher state persists across module reloads."""
    # This test would verify watcher persistence - implementation depends on
    # how watcher state is stored (global dict, file, etc.)
    # Placeholder for actual implementation
    pass


# ============================================================================
# TEST: Integration Workflow
# ============================================================================


@pytest.mark.asyncio
async def test_full_workflow_new_project(temp_project, mock_store):
    """Test complete workflow: no index → prompt Y → create index → start watcher → search."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.semantic_index") as mock_index, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher") as mock_watcher, \
         patch("mcp_bridge.tools.semantic_search.get_file_watcher", return_value=None), \
         patch("builtins.input", return_value="y"):

        # Start with no index
        mock_store.collection.count.return_value = 0
        mock_get_store.return_value = mock_store

        from mcp_bridge.tools.semantic_search import semantic_search

        # First call: no index, should prompt
        await semantic_search("find auth", project_path=temp_project)

        # Verify workflow
        assert mock_index.call_count == 1
        assert mock_watcher.call_count == 1

        # Simulate index now exists
        mock_store.collection.count.return_value = 100
        mock_store.search.return_value = []

        # Second call: index exists, should work directly
        await semantic_search("find db", project_path=temp_project)

        # Index should not be created again
        assert mock_index.call_count == 1


@pytest.mark.asyncio
async def test_full_workflow_existing_index(temp_project, mock_store):
    """Test workflow when index already exists: skip prompt → start watcher → search."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher") as mock_watcher, \
         patch("mcp_bridge.tools.semantic_search.get_file_watcher", return_value=None), \
         patch("builtins.input") as mock_input:

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 100  # Index exists
        mock_store.search.return_value = []

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        # Should NOT prompt (index exists)
        mock_input.assert_not_called()

        # Should start watcher
        mock_watcher.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
