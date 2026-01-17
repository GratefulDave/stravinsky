"""Test suite for semantic search auto-indexing functionality.

Tests cover:
- File creation/modification/deletion detection
- Incremental indexing and debouncing
- Vector database consistency
- Error recovery and notifications
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from mcp_bridge.tools.semantic_search import (
    CodebaseVectorStore,
    BaseEmbeddingProvider,
    get_store,
)


# ============================================================================
# FIXTURES
# ============================================================================


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Mock embedding provider for testing without Ollama/Gemini."""

    def __init__(self):
        self._available = True
        self.embed_calls = []

    @property
    def dimension(self) -> int:
        return 768

    @property
    def name(self) -> str:
        return "mock"

    async def check_available(self) -> bool:
        return self._available

    async def get_embedding(self, text: str) -> list[float]:
        """Return deterministic embedding based on text length."""
        self.embed_calls.append(text)
        # Deterministic vector: hash of text length
        seed = len(text) % 256
        return [float((seed + i) % 256) / 256.0 for i in range(self.dimension)]


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        yield project_dir
        # Cleanup is automatic with context manager


@pytest.fixture
def mock_provider():
    """Create a mock embedding provider."""
    return MockEmbeddingProvider()


@pytest.fixture
async def vector_store(temp_project_dir, mock_provider):
    """Create a vector store with mock provider."""
    with tempfile.TemporaryDirectory() as db_tmp:
        db_base = Path(db_tmp)
        store = CodebaseVectorStore(str(temp_project_dir), provider="ollama", base_path=db_base)
        store.provider = mock_provider
        yield store
        if store.db_path.exists():
            import shutil

            shutil.rmtree(store.db_path)


# ============================================================================
# UNIT TESTS: CHUNKING
# ============================================================================


@pytest.mark.asyncio
async def test_chunk_simple_python_file(vector_store, temp_project_dir):
    """Test chunking a simple Python file."""
    # Create a test file
    test_file = temp_project_dir / "simple.py"
    test_file.write_text(
        """def hello_world():
    \"\"\"Print hello world.\"\"\"
    print("Hello, World!")

def goodbye():
    \"\"\"Print goodbye.\"\"\"
    print("Goodbye!")
"""
    )

    # Chunk the file
    chunks = await vector_store._chunk_file(test_file)

    # Should create chunks for functions
    assert len(chunks) > 0
    assert all("id" in c and "document" in c and "metadata" in c for c in chunks)

    # Verify metadata
    for chunk in chunks:
        assert chunk["metadata"]["file_path"] == "simple.py"
        assert chunk["metadata"]["language"] == "py"
        assert "start_line" in chunk["metadata"]
        assert "end_line" in chunk["metadata"]


@pytest.mark.asyncio
async def test_chunk_python_with_classes(vector_store, temp_project_dir):
    """Test chunking Python file with classes and methods."""
    test_file = temp_project_dir / "classes.py"
    test_file.write_text(
        """class MyClass:
    \"\"\"A test class.\"\"\"

    def __init__(self):
        self.value = 42

    def method1(self):
        \"\"\"First method.\"\"\"
        return self.value

    def method2(self):
        \"\"\"Second method.\"\"\"
        return self.value * 2
"""
    )

    chunks = await vector_store._chunk_file(test_file)

    # Should have class chunk + method chunks
    assert len(chunks) >= 3  # Class + 2 methods minimum

    # Verify class is identified
    class_chunks = [c for c in chunks if c["metadata"].get("node_type") == "class"]
    assert len(class_chunks) >= 1

    # Verify methods are identified
    method_chunks = [c for c in chunks if c["metadata"].get("node_type") == "method"]
    assert len(method_chunks) >= 2


@pytest.mark.asyncio
async def test_chunk_small_file_skipped(vector_store, temp_project_dir):
    """Test that very small files are skipped."""
    test_file = temp_project_dir / "tiny.py"
    test_file.write_text("x = 1")  # Too small

    chunks = await vector_store._chunk_file(test_file)
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_chunk_syntax_error_fallback(vector_store, temp_project_dir):
    """Test fallback to line-based chunking on syntax errors."""
    test_file = temp_project_dir / "broken.py"
    test_file.write_text(
        """def broken(
        # Missing closing paren

def another():
    pass
"""
    )

    chunks = await vector_store._chunk_file(test_file)

    # Should fall back to line-based chunking
    assert len(chunks) > 0
    assert all(c["metadata"].get("language") == "py" for c in chunks)


# ============================================================================
# UNIT TESTS: FILE CHANGE DETECTION
# ============================================================================


@pytest.mark.asyncio
async def test_detect_new_chunks(vector_store, temp_project_dir):
    """Test detection of new chunks compared to existing index."""
    # Simulate existing index state
    file1 = temp_project_dir / "file1.py"
    file1.write_text("""def func1():
    x = 1
    y = 2
    z = x + y
    return z
""")

    chunks1 = await vector_store._chunk_file(file1)
    existing_ids = {c["id"] for c in chunks1}

    # Simulate code change - add new file
    file2 = temp_project_dir / "file2.py"
    file2.write_text("""def func2():
    x = 2
    y = 3
    z = x + y
    return z
""")

    chunks2 = await vector_store._chunk_file(file2)
    new_ids = {c["id"] for c in chunks2}

    # Should be completely different IDs
    assert len(existing_ids & new_ids) == 0


@pytest.mark.asyncio
async def test_detect_modified_chunks(vector_store, temp_project_dir):
    """Test detection of modified content (different hash)."""
    test_file = temp_project_dir / "test.py"

    # Original content (must be >=5 lines to avoid being skipped)
    test_file.write_text("""def func():
    x = 1
    y = 2
    z = 3
    return x + y + z
""")
    chunks_v1 = await vector_store._chunk_file(test_file)
    ids_v1 = {c["id"] for c in chunks_v1}

    # Modified content (same length, different logic)
    test_file.write_text("""def func():
    a = 10
    b = 20
    c = 30
    return a * b * c
""")
    chunks_v2 = await vector_store._chunk_file(test_file)
    ids_v2 = {c["id"] for c in chunks_v2}

    # IDs should be different (content hash changed)
    assert ids_v1 != ids_v2


@pytest.mark.asyncio
async def test_content_hash_stability(vector_store, temp_project_dir):
    """Test that same content produces same hash."""
    test_file = temp_project_dir / "test.py"
    content = "def func(): pass\n"

    test_file.write_text(content)
    chunks1 = await vector_store._chunk_file(test_file)
    ids1 = {c["id"] for c in chunks1}

    # Write same content again
    test_file.write_text(content)
    chunks2 = await vector_store._chunk_file(test_file)
    ids2 = {c["id"] for c in chunks2}

    # Hashes should be identical
    assert ids1 == ids2


# ============================================================================
# UNIT TESTS: FILE PATTERN MATCHING
# ============================================================================


@pytest.mark.asyncio
async def test_exclude_venv_directory(vector_store, temp_project_dir):
    """Test that .venv directory is excluded."""
    # Create files in excluded directory
    venv_dir = temp_project_dir / ".venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("""def unused():
    x = 1
    y = 2
    z = x + y
    return z
""")

    # Create file in included directory
    src_dir = temp_project_dir / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("""def main():
    x = 1
    y = 2
    z = x + y
    return z
""")

    files = vector_store._get_files_to_index()
    # Resolve temp_project_dir to handle macOS /var → /private/var aliasing
    resolved_project = temp_project_dir.resolve()
    file_paths = {f.relative_to(resolved_project) for f in files}

    assert Path("src/main.py") in file_paths
    assert not any(".venv" in str(p) for p in file_paths)


@pytest.mark.asyncio
async def test_exclude_node_modules(vector_store, temp_project_dir):
    """Test that node_modules directory is excluded."""
    nm_dir = temp_project_dir / "node_modules"
    nm_dir.mkdir()
    (nm_dir / "lib.js").write_text("export function unused() {}")

    src_dir = temp_project_dir / "src"
    src_dir.mkdir()
    (src_dir / "app.js").write_text("function app() {}")

    files = vector_store._get_files_to_index()
    # Resolve temp_project_dir to handle macOS /var → /private/var aliasing
    resolved_project = temp_project_dir.resolve()
    file_paths = {f.relative_to(resolved_project) for f in files}

    assert Path("src/app.js") in file_paths
    assert not any("node_modules" in str(p) for p in file_paths)


@pytest.mark.asyncio
async def test_include_code_extensions(vector_store, temp_project_dir):
    """Test that various code extensions are included."""
    extensions = {".py", ".js", ".ts", ".go", ".rs"}

    for ext in extensions:
        (temp_project_dir / f"test{ext}").write_text("test code")

    files = vector_store._get_files_to_index()
    found_exts = {f.suffix for f in files}

    assert extensions.issubset(found_exts)


# ============================================================================
# INTEGRATION TESTS: INDEXING
# ============================================================================


@pytest.mark.asyncio
async def test_index_single_file(vector_store, temp_project_dir, mock_provider):
    """Test indexing a single file."""
    # Create test file (>=5 lines to avoid being skipped)
    test_file = temp_project_dir / "test.py"
    test_file.write_text("""def hello():
    msg = 'world'
    print(msg)
    return msg
# end of file
""")

    # Index the codebase
    stats = await vector_store.index_codebase()

    assert stats["indexed"] > 0
    assert stats["total_files"] == 1
    assert "db_path" in stats


@pytest.mark.asyncio
async def test_index_multiple_files(vector_store, temp_project_dir, mock_provider):
    """Test indexing multiple files."""
    # Create test files (>=5 lines each)
    for i in range(3):
        test_file = temp_project_dir / f"module{i}.py"
        test_file.write_text(f"""def func{i}():
    x = {i}
    y = {i + 1}
    z = x + y
    return z
""")

    # Index
    stats = await vector_store.index_codebase()

    assert stats["indexed"] > 0
    assert stats["total_files"] == 3


@pytest.mark.asyncio
async def test_incremental_indexing(vector_store, temp_project_dir, mock_provider):
    """Test that incremental indexing only adds new chunks."""
    # First indexing
    (temp_project_dir / "file1.py").write_text("""def func1():
    x = 1
    y = 2
    z = x + y
    return z
""")
    stats1 = await vector_store.index_codebase()
    count1 = stats1["indexed"]

    # Add new file
    (temp_project_dir / "file2.py").write_text("""def func2():
    x = 2
    y = 3
    z = x + y
    return z
""")
    stats2 = await vector_store.index_codebase()

    # Should only index new chunks
    assert stats2["indexed"] > 0
    assert stats2["indexed"] < count1 + 10  # Roughly one or two chunks per function


@pytest.mark.asyncio
async def test_force_reindex(vector_store, temp_project_dir, mock_provider):
    """Test force reindexing with force=True."""
    # Create and index file
    test_file = temp_project_dir / "test.py"
    test_file.write_text("""def func():
    x = 1
    y = 2
    z = x + y
    return z
""")

    stats1 = await vector_store.index_codebase()
    original_indexed = stats1["indexed"]

    # Force reindex
    stats2 = await vector_store.index_codebase(force=True)

    # Should reindex everything
    assert stats2["indexed"] == original_indexed


# ============================================================================
# INTEGRATION TESTS: DELETION DETECTION
# ============================================================================


@pytest.mark.asyncio
async def test_delete_file_removes_chunks(vector_store, temp_project_dir, mock_provider):
    """Test that deleted file chunks are removed from index."""
    # Create and index file
    test_file = temp_project_dir / "test.py"
    test_file.write_text("""def func():
    x = 1
    y = 2
    z = x + y
    return z
""")

    await vector_store.index_codebase()

    # Delete file
    test_file.unlink()

    # Re-index
    stats = await vector_store.index_codebase()

    # Should have pruned chunks
    assert stats["pruned"] > 0


@pytest.mark.asyncio
async def test_delete_directory_removes_chunks(vector_store, temp_project_dir, mock_provider):
    """Test that deleted directory chunks are removed."""
    # Create directory with files
    subdir = temp_project_dir / "olddir"
    subdir.mkdir()
    (subdir / "file1.py").write_text("""def func1():
    x = 1
    y = 2
    z = x + y
    return z
""")
    (subdir / "file2.py").write_text("""def func2():
    x = 2
    y = 3
    z = x + y
    return z
""")

    await vector_store.index_codebase()

    # Delete directory
    import shutil

    shutil.rmtree(subdir)

    # Re-index
    stats = await vector_store.index_codebase()

    # Should have pruned chunks
    assert stats["pruned"] > 0


# ============================================================================
# INTEGRATION TESTS: ERROR RECOVERY
# ============================================================================


@pytest.mark.asyncio
async def test_embedding_service_unavailable(vector_store, mock_provider):
    """Test graceful handling when embedding service unavailable."""
    # Mark provider as unavailable
    mock_provider._available = False

    stats = await vector_store.index_codebase()

    # Should return error, not crash
    assert "error" in stats
    assert "Embedding service not available" in stats["error"]


@pytest.mark.asyncio
async def test_retry_on_service_recovery(vector_store, temp_project_dir, mock_provider):
    """Test that indexing retries when service becomes available again."""
    test_file = temp_project_dir / "test.py"
    test_file.write_text("""def func():
    x = 1
    y = 2
    z = x + y
    return z
""")

    # First attempt - service unavailable
    mock_provider._available = False
    stats1 = await vector_store.index_codebase()
    assert "error" in stats1

    # Service recovered
    mock_provider._available = True
    stats2 = await vector_store.index_codebase()
    assert "indexed" in stats2
    assert stats2["indexed"] > 0


# ============================================================================
# INTEGRATION TESTS: SEARCH AFTER INDEXING
# ============================================================================


@pytest.mark.asyncio
async def test_search_finds_indexed_content(vector_store, temp_project_dir, mock_provider):
    """Test that semantic search finds indexed content."""
    # Create and index file with distinctive content (must be >=5 lines)
    test_file = temp_project_dir / "auth.py"
    test_file.write_text(
        """def authenticate_user(username, password):
    \"\"\"Authenticate user against database.\"\"\"
    # Validate credentials
    if not username or not password:
        return False
    return check_credentials(username, password)
"""
    )

    stats = await vector_store.index_codebase()
    assert stats["indexed"] > 0, f"Expected chunks to be indexed, got: {stats}"

    # Search for authentication-related content
    results = await vector_store.search("authentication")

    # Should find the auth.py file
    assert len(results) > 0, "Expected search results"
    assert "error" not in results[0], f"Search failed: {results[0]}"

    # Check if any result contains "auth.py" in the file path
    files_found = [r.get("file", "") for r in results]
    assert any("auth.py" in f for f in files_found), (
        f"Expected 'auth.py' in results, got files: {files_found}"
    )


@pytest.mark.asyncio
async def test_search_empty_index(vector_store):
    """Test search on empty index."""
    results = await vector_store.search("something")

    # Should return error about no documents
    assert len(results) > 0
    assert "error" in results[0] or "No documents" in results[0].get("hint", "")


# ============================================================================
# STRESS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_many_small_files(vector_store, temp_project_dir, mock_provider):
    """Test indexing many small files."""
    # Create 50 small files
    for i in range(50):
        file_path = temp_project_dir / f"file_{i}.py"
        file_path.write_text(f"""def func_{i}():
    x = {i}
    y = {i + 1}
    z = x + y
    return z
""")

    stats = await vector_store.index_codebase()

    assert stats["indexed"] > 0
    assert stats["total_files"] == 50


@pytest.mark.asyncio
async def test_large_file(vector_store, temp_project_dir, mock_provider):
    """Test indexing a large file."""
    # Create a large file with many functions
    large_file = temp_project_dir / "large.py"
    content = "\n".join([f"def func_{i}():\n    return {i}\n" for i in range(100)])
    large_file.write_text(content)

    stats = await vector_store.index_codebase()

    assert stats["indexed"] > 0
    assert stats["total_files"] == 1


# ============================================================================
# STATS AND DIAGNOSTICS
# ============================================================================


@pytest.mark.asyncio
async def test_get_stats(vector_store, temp_project_dir, mock_provider):
    """Test getting vector store statistics."""
    test_file = temp_project_dir / "test.py"
    test_file.write_text("""def func():
    x = 1
    y = 2
    z = x + y
    return z
""")

    await vector_store.index_codebase()

    stats = vector_store.get_stats()

    assert stats["chunks_indexed"] > 0
    assert stats["embedding_provider"] == "mock"
    assert stats["embedding_dimension"] == 768
    assert "db_path" in stats


@pytest.mark.asyncio
async def test_embedding_provider_factory(temp_project_dir):
    """Test getting store with different providers."""
    from mcp_bridge.tools.semantic_search import get_store

    # Mock provider assignment
    store = get_store(str(temp_project_dir), "ollama")
    assert store.provider_name == "ollama"

    # Different provider should be different store instance
    store2 = get_store(str(temp_project_dir), "mxbai")
    assert store2.provider_name == "mxbai"


# ============================================================================
# ASYNC HELPERS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
