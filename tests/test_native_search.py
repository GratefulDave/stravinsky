import pytest
import os
import stravinsky_native

@pytest.fixture
def test_dir(tmp_path):
    """Create a test directory with some files."""
    d = tmp_path / "search_test"
    d.mkdir()
    (d / "file1.txt").write_text("Hello world")
    (d / "file2.py").write_text("print('test')")
    (d / "subdir").mkdir()
    (d / "subdir" / "file3.txt").write_text("Another hello")
    return d

def test_native_glob_files(test_dir):
    """Test glob_files implementation."""
    # This should fail initially as glob_files is not implemented
    if not hasattr(stravinsky_native, "glob_files"):
        pytest.fail("stravinsky_native.glob_files not implemented")
        
    results = stravinsky_native.glob_files(str(test_dir), "**/*.txt")
    assert len(results) == 2
    assert any("file1.txt" in r for r in results)
    assert any("file3.txt" in r for r in results)

def test_native_grep_search(test_dir):
    """Test grep_search implementation."""
    if not hasattr(stravinsky_native, "grep_search"):
        pytest.fail("stravinsky_native.grep_search not implemented")
        
    # pattern, directory
    results = stravinsky_native.grep_search("hello", str(test_dir))
    # Should find file1.txt and file3.txt
    assert len(results) == 2
    # Expecting list of dicts or tuples: (file_path, line_number, line_content)
    filenames = [r["path"] for r in results]
    assert any("file1.txt" in f for f in filenames)
    assert any("file3.txt" in f for f in filenames)
