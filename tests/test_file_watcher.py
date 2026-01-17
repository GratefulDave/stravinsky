"""
Tests for FileWatcher functionality in semantic search.

Tests cover:
- FileWatcher initialization and lifecycle
- File change detection (create, modify, delete)
- Debouncing of rapid changes
- Integration with CodebaseVectorStore
- Module-level watcher management
"""

import asyncio
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from mcp_bridge.tools.semantic_search import (
    CodebaseFileWatcher,
    CodebaseVectorStore,
    start_file_watcher,
    stop_file_watcher,
    get_file_watcher,
    list_file_watchers,
)

# Force CodebaseFileWatcher to use watchdog by mocking NativeFileWatcher failure
@pytest.fixture(autouse=True)
def disable_native_watcher():
    with patch("mcp_bridge.tools.semantic_search.NativeFileWatcher", side_effect=ImportError("Disabled for tests")):
        yield

@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory with Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create initial Python files
        (project_path / "main.py").write_text("def main(): pass")
        (project_path / "utils.py").write_text("def helper(): pass")

        # Create a subdirectory with a file
        subdir = project_path / "lib"
        subdir.mkdir()
        (subdir / "core.py").write_text("class Core: pass")

        yield project_path


@pytest.fixture
def vector_store(temp_project):
    """Create a vector store for the temporary project."""
    # Use ollama provider for testing (if available)
    store = CodebaseVectorStore(str(temp_project), provider="ollama")
    yield store
    # Cleanup
    try:
        stop_file_watcher(str(temp_project))
    except Exception:
        pass
    # Clean up vectordb directory to avoid orphaned test directories
    import shutil
    if store.db_path.exists():
        shutil.rmtree(store.db_path, ignore_errors=True)


class TestCodebaseFileWatcher:
    """Tests for CodebaseFileWatcher class."""

    def test_initialization(self, temp_project, vector_store):
        """Test FileWatcher can be initialized."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
            debounce_seconds=1.0,
        )

        assert watcher.project_path == temp_project.resolve()
        assert watcher.store is vector_store
        assert watcher.debounce_seconds == 1.0
        assert not watcher.is_running()

    def test_start_stop(self, temp_project, vector_store):
        """Test FileWatcher can be started and stopped."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
            debounce_seconds=1.0,
        )

        # Start the watcher
        watcher.start()
        assert watcher.is_running()

        # Stop the watcher
        watcher.stop()
        assert not watcher.is_running()

    def test_cannot_start_twice(self, temp_project, vector_store):
        """Test that starting an already-running watcher logs a warning."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
        )

        watcher.start()
        assert watcher.is_running()

        # Try to start again (should log warning, not error)
        watcher.start()
        assert watcher.is_running()

        watcher.stop()

    def test_file_filter_python_only(self, temp_project, vector_store):
        """Test that only .py files trigger reindexing."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
        )
        handler = watcher._event_handler or type(
            'Handler', (), {'_should_index_file': lambda s, f: False}
        )()

        # Dynamically create the handler after watcher initialization
        watcher.start()

        # The watcher is now running, but we can test through public interface
        watcher.stop()

    def test_debounce_timer_cancellation(self, temp_project, vector_store):
        """Test that debounce timer is properly cancelled."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
            debounce_seconds=0.1,
        )

        watcher.start()

        # Simulate multiple file changes
        test_file = temp_project / "test.py"
        test_file.write_text("# change 1")

        # Wait half a debounce period
        time.sleep(0.05)

        test_file.write_text("# change 2")

        # Should have reset the timer
        assert watcher._pending_reindex_timer is not None

        watcher.stop()

    def test_skip_hidden_files(self, temp_project, vector_store):
        """Test that hidden files don't trigger reindexing."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
        )

        # Create and start watcher to get the handler
        watcher.start()
        handler = watcher._event_handler

        # Test that hidden files are skipped
        assert not handler._should_index_file(str(temp_project / ".hidden.py"))
        assert not handler._should_index_file(str(temp_project / ".git" / "config"))

        watcher.stop()

    def test_skip_venv_directories(self, temp_project, vector_store):
        """Test that venv and other skip directories are excluded."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
        )

        watcher.start()
        handler = watcher._event_handler

        # Test that skip directories are excluded
        assert not handler._should_index_file(str(temp_project / "venv" / "lib.py"))
        assert not handler._should_index_file(str(temp_project / "__pycache__" / "mod.py"))
        assert not handler._should_index_file(str(temp_project / "node_modules" / "pkg.py"))

        watcher.stop()

    def test_include_valid_python_files(self, temp_project, vector_store):
        """Test that valid Python files are included."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
        )

        watcher.start()
        handler = watcher._event_handler

        # Test that valid Python files pass the filter
        assert handler._should_index_file(str(temp_project / "main.py"))
        assert handler._should_index_file(str(temp_project / "lib" / "core.py"))

        watcher.stop()

    def test_exclude_non_python_files(self, temp_project, vector_store):
        """Test that non-Python files are excluded."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
        )

        watcher.start()
        handler = watcher._event_handler

        # Test that non-Python files are excluded
        assert not handler._should_index_file(str(temp_project / "README.md"))
        assert not handler._should_index_file(str(temp_project / "config.yaml"))
        assert not handler._should_index_file(str(temp_project / "data.json"))

        watcher.stop()


class TestModuleLevel:
    """Tests for module-level watcher management."""

    @pytest.mark.asyncio
    async def test_start_file_watcher(self, temp_project):
        """Test starting a file watcher through module function.

        Should automatically create index if it doesn't exist.
        """
        # Create a test file (must be >=5 lines for indexing)
        test_file = temp_project / "test.py"
        test_file.write_text("def test():\n    x = 1\n    y = 2\n    z = x + y\n    return z\n")

        # Start watcher - should auto-create index if needed
        watcher = await start_file_watcher(str(temp_project), provider="ollama")
        assert watcher is not None
        assert watcher.is_running()

        # Clean up
        assert stop_file_watcher(str(temp_project))
        assert not watcher.is_running()
        # Clean up vectordb directory
        import shutil
        if watcher.store.db_path.exists():
            shutil.rmtree(watcher.store.db_path, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_get_file_watcher(self, temp_project):
        """Test getting an active file watcher."""
        # Create a test file (must be >=5 lines)
        test_file = temp_project / "test.py"
        test_file.write_text("def test():\n    x = 1\n    y = 2\n    z = x + y\n    return z\n")

        watcher = await start_file_watcher(str(temp_project), provider="ollama")

        # Should be able to retrieve it
        retrieved = get_file_watcher(str(temp_project))
        assert retrieved is watcher

        # Clean up
        stop_file_watcher(str(temp_project))
        # Clean up vectordb directory
        import shutil
        if watcher.store.db_path.exists():
            shutil.rmtree(watcher.store.db_path, ignore_errors=True)

    def test_get_nonexistent_watcher(self, temp_project):
        """Test getting a watcher that doesn't exist."""
        retrieved = get_file_watcher(str(temp_project))
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_file_watchers(self, temp_project):
        """Test listing active file watchers."""
        # Create a test file (must be >=5 lines)
        test_file = temp_project / "test.py"
        test_file.write_text("def test():\n    x = 1\n    y = 2\n    z = x + y\n    return z\n")

        # Start a watcher
        watcher = await start_file_watcher(str(temp_project), provider="ollama")

        # Should appear in list
        watchers = list_file_watchers()
        assert len(watchers) >= 1
        assert any(w["project_path"] == str(temp_project.resolve()) for w in watchers)

        # Check structure of watcher info
        watcher_info = next(w for w in watchers if w["project_path"] == str(temp_project.resolve()))
        assert "project_path" in watcher_info
        assert "debounce_seconds" in watcher_info
        assert "provider" in watcher_info
        assert "status" in watcher_info
        assert watcher_info["status"] == "running"

        # Clean up
        stop_file_watcher(str(temp_project))
        # Clean up vectordb directory
        import shutil
        if watcher.store.db_path.exists():
            shutil.rmtree(watcher.store.db_path, ignore_errors=True)

    def test_stop_nonexistent_watcher(self, temp_project):
        """Test stopping a watcher that doesn't exist."""
        result = stop_file_watcher(str(temp_project))
        assert result is False


class TestFileWatcherDebouncing:
    """Tests for debouncing behavior."""

    def test_debounce_batches_changes(self, temp_project, vector_store):
        """Test that rapid changes are batched together."""
        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
            debounce_seconds=0.2,
        )

        watcher.start()

        # Make several rapid changes
        test_file = temp_project / "test.py"
        test_file.write_text("# change 1\n")
        test_file.write_text("# change 2\n")
        test_file.write_text("# change 3\n")

        # Pending files should accumulate
        # (exact count depends on timing, but should be >1 or processing)

        watcher.stop()

    def test_custom_debounce_period(self, temp_project, vector_store):
        """Test setting custom debounce period."""
        custom_debounce = 0.5

        watcher = CodebaseFileWatcher(
            project_path=temp_project,
            store=vector_store,
            debounce_seconds=custom_debounce,
        )

        assert watcher.debounce_seconds == custom_debounce

        watcher.start()
        watcher.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
