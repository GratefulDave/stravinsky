"""Test symlink boundary validation for semantic search indexing.

Ensures that symlinks pointing outside the project directory are NOT indexed,
preventing potential security issues and unintended file access.
"""

import tempfile
from pathlib import Path

import pytest

from mcp_bridge.tools.semantic_search import CodebaseVectorStore


class MockEmbeddingProvider:
    """Mock embedding provider for testing without external dependencies."""

    def __init__(self):
        self._available = True

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
        seed = len(text) % 256
        return [float((seed + i) % 256) / 256.0 for i in range(self.dimension)]


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        yield project_dir


@pytest.fixture
def mock_provider():
    """Create a mock embedding provider."""
    return MockEmbeddingProvider()


@pytest.fixture
async def vector_store(temp_project_dir, mock_provider):
    """Create a vector store with mock provider."""
    store = CodebaseVectorStore(str(temp_project_dir), provider="ollama")
    # Replace provider with mock
    store.provider = mock_provider
    yield store
    # Cleanup: delete the test database
    import shutil
    if store.db_path.exists():
        shutil.rmtree(store.db_path)


@pytest.mark.asyncio
async def test_symlink_boundary_validation(vector_store, temp_project_dir):
    """Test that symlinks pointing outside project boundaries are NOT indexed.

    Security test: Ensures _get_files_to_index() properly validates that
    symlinks cannot be used to index files outside the project directory.
    """
    # Create external directory and file (outside project)
    with tempfile.TemporaryDirectory() as external_tmpdir:
        external_dir = Path(external_tmpdir) / "outside"
        external_dir.mkdir()
        external_file = external_dir / "external.py"
        external_file.write_text("def external_function(): pass")

        # Create internal file (inside project)
        internal_file = temp_project_dir / "code.py"
        internal_file.write_text("def internal_function(): pass")

        # Create symlink inside project pointing to external file
        symlink_path = temp_project_dir / "external_link.py"
        try:
            symlink_path.symlink_to(external_file)
        except OSError:
            # Skip test if symlinks not supported (e.g., Windows without admin)
            pytest.skip("Symlinks not supported on this system")

        # Get files to index
        files = vector_store._get_files_to_index()

        # Resolve paths to handle macOS /var -> /private/var symlink
        project_resolved = temp_project_dir.resolve()
        file_paths = {f.resolve().relative_to(project_resolved) for f in files}

        # Verify only internal file is indexed
        assert Path("code.py") in file_paths, "Internal file should be indexed"
        assert Path("external_link.py") not in file_paths, "Symlink to external file should NOT be indexed"

        # Ensure no external paths leaked in
        for file_path in files:
            resolved = file_path.resolve()
            try:
                resolved.relative_to(project_resolved)
            except ValueError:
                pytest.fail(
                    f"File {file_path} resolves to {resolved} which is outside "
                    f"project {project_resolved}. Boundary validation failed!"
                )


@pytest.mark.asyncio
async def test_symlink_to_internal_directory(vector_store, temp_project_dir):
    """Test that symlinks to internal directories ARE followed (valid use case).

    Ensures internal symlinks still work for legitimate project organization.
    """
    # Create real directory with file
    real_dir = temp_project_dir / "real_dir"
    real_dir.mkdir()
    real_file = real_dir / "real.py"
    real_file.write_text("def real_function(): pass")

    # Create symlink to internal directory
    symlink_dir = temp_project_dir / "symlink_dir"
    try:
        symlink_dir.symlink_to(real_dir)
    except OSError:
        pytest.skip("Symlinks not supported on this system")

    # Get files to index
    files = vector_store._get_files_to_index()

    # Resolve paths to handle macOS /var -> /private/var symlink
    project_resolved = temp_project_dir.resolve()
    file_paths = {f.resolve().relative_to(project_resolved) for f in files}

    # Should index the file (accessible via both paths)
    # Note: The actual path indexed depends on rglob() traversal order
    assert len(file_paths) > 0, "Should index at least one file"
    assert any("real.py" in str(p) for p in file_paths), "Should find real.py"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
