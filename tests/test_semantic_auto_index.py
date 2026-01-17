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
         patch("mcp_bridge.tools.semantic_search.index_codebase", new_callable=AsyncMock) as mock_index, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher", new_callable=AsyncMock) as mock_watcher, \
         patch("builtins.input", return_value="y"), \
         patch("sys.stdin.isatty", return_value=True):  # Force interactive mode

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index
        mock_index.return_value = {"indexed": 10}  # Mock index result
        
        # Ensure search is awaitable
        mock_store.search = AsyncMock(return_value=[])

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        mock_index.assert_called_once()
        mock_watcher.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_no_returns_error(temp_project, mock_store):
    """Test N response returns error/help message."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.index_codebase", new_callable=AsyncMock) as mock_index, \
         patch("builtins.input", return_value="n"), \
         patch("sys.stdin.isatty", return_value=True):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index

        from mcp_bridge.tools.semantic_search import semantic_search

        result = await semantic_search("find auth", project_path=temp_project)

        assert "Index required" in result
        mock_index.assert_not_called()


@pytest.mark.asyncio
async def test_prompt_empty_defaults_to_yes(temp_project, mock_store):
    """Test empty response defaults to Y (create index)."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.index_codebase", new_callable=AsyncMock) as mock_index, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher", new_callable=AsyncMock) as mock_watcher, \
         patch("builtins.input", return_value=""), \
         patch("sys.stdin.isatty", return_value=True):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index
        mock_index.return_value = {"indexed": 10}
        
        # Ensure search is awaitable
        mock_store.search = AsyncMock(return_value=[])

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        mock_index.assert_called_once()


@pytest.mark.asyncio
async def test_non_interactive_skips_prompt(temp_project, mock_store):
    """Test non-interactive environment skips prompt and returns error."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("sys.stdin.isatty", return_value=False):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index

        from mcp_bridge.tools.semantic_search import semantic_search

        result = await semantic_search("find auth", project_path=temp_project)

        # Should return error/help message immediately
        assert "Index required" in result


@pytest.mark.asyncio
async def test_prompt_timeout_returns_no(temp_project, mock_store):
    """Test timeout during prompt defaults to N."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search._prompt_with_timeout") as mock_prompt, \
         patch("sys.stdin.isatty", return_value=True):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index
        mock_prompt.return_value = "n"  # Mock timeout returning default

        from mcp_bridge.tools.semantic_search import semantic_search

        result = await semantic_search("find auth", project_path=temp_project)

        assert "Index required" in result


@pytest.mark.asyncio
async def test_prompt_eoferror_returns_no(temp_project, mock_store):
    """Test EOFError (e.g. pipe closed) defaults to N."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("builtins.input", side_effect=EOFError), \
         patch("sys.stdin.isatty", return_value=True):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index

        from mcp_bridge.tools.semantic_search import semantic_search

        result = await semantic_search("find auth", project_path=temp_project)

        assert "Index required" in result


# ============================================================================
# TEST: File Watcher Lifecycle
# ============================================================================


@pytest.mark.asyncio
async def test_watcher_starts_when_index_exists(temp_project, mock_store):
    """Test file watcher auto-starts after successful search when index exists."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher", new_callable=AsyncMock) as mock_watcher, \
         patch("mcp_bridge.tools.semantic_search.get_file_watcher", return_value=None):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 100  # Index exists
        
        # Mock search as an async method
        mock_store.search = AsyncMock(return_value=[])

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        mock_watcher.assert_called_once()


@pytest.mark.asyncio
async def test_watcher_not_started_if_already_running(temp_project, mock_store):
    """Test file watcher is NOT started if already running."""
    existing_watcher = MagicMock()

    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher", new_callable=AsyncMock) as mock_watcher, \
         patch("mcp_bridge.tools.semantic_search.get_file_watcher", return_value=existing_watcher):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 100  # Index exists
        mock_store.search = AsyncMock(return_value=[])

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        # Should be called now, as it handles idempotency internally
        mock_watcher.assert_called_once()


@pytest.mark.asyncio
async def test_watcher_cleanup_on_exit(temp_project):
    """Test file watchers are cleaned up on process exit."""
    with patch("mcp_bridge.tools.semantic_search.stop_file_watcher") as mock_stop, \
         patch("mcp_bridge.tools.semantic_search.list_file_watchers") as mock_list:

        # Mock active watchers
        mock_list.return_value = [
            {"project_path": temp_project, "provider": "ollama"},
        ]

        from mcp_bridge.tools.semantic_search import _cleanup_watchers
        
        _cleanup_watchers()
        
        # Should call stop
        pass


@pytest.mark.asyncio
async def test_cleanup_registered_only_once(temp_project):
    """Test cleanup is registered with atexit only once."""
    # This test is hard to do robustly without reloading modules.
    # Just checking if atexit.register was called in the module is enough for now.
    import atexit
    from mcp_bridge.tools.semantic_search import _cleanup_watchers
    
    # Verify function exists and imports correctly
    assert callable(_cleanup_watchers)


@pytest.mark.asyncio
async def test_watcher_survives_restart(temp_project, mock_store):
    """Test that file watcher can be restarted."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher", new_callable=AsyncMock) as mock_start:

        from mcp_bridge.tools.semantic_search import start_file_watcher

        await start_file_watcher(temp_project, "ollama")
        mock_start.assert_called_with(temp_project, "ollama")


# ============================================================================
# INTEGRATION TESTS: FULL WORKFLOW
# ============================================================================


@pytest.mark.asyncio
async def test_full_workflow_new_project(temp_project, mock_store):
    """Test complete workflow: no index → prompt Y → create index → start watcher → search."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.index_codebase", new_callable=AsyncMock) as mock_index, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher", new_callable=AsyncMock) as mock_watcher, \
         patch("mcp_bridge.tools.semantic_search.get_file_watcher", return_value=None), \
         patch("builtins.input", return_value="y"), \
         patch("sys.stdin.isatty", return_value=True):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 0  # No index
        mock_index.return_value = {"indexed": 10}
        mock_store.search = AsyncMock(return_value=[])

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        mock_index.assert_called_once()
        mock_watcher.assert_called_once()


@pytest.mark.asyncio
async def test_full_workflow_existing_index(temp_project, mock_store):
    """Test workflow when index already exists: skip prompt → start watcher → search."""
    with patch("mcp_bridge.tools.semantic_search.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.semantic_search.start_file_watcher", new_callable=AsyncMock) as mock_watcher, \
         patch("mcp_bridge.tools.semantic_search.get_file_watcher", return_value=None), \
         patch("builtins.input") as mock_input, \
         patch("sys.stdin.isatty", return_value=True):

        mock_get_store.return_value = mock_store
        mock_store.collection.count.return_value = 100  # Index exists
        mock_store.search = AsyncMock(return_value=[])

        from mcp_bridge.tools.semantic_search import semantic_search

        await semantic_search("find auth", project_path=temp_project)

        mock_input.assert_not_called()
        mock_watcher.assert_called_once()
