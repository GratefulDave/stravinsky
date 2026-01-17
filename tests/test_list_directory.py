import pytest
import os
from pathlib import Path
from mcp_bridge.tools.list_directory import list_directory
from mcp_bridge.utils.cache import IOCache

@pytest.mark.asyncio
async def test_list_directory_basic(tmp_path):
    # Create some files
    (tmp_path / "file1.txt").write_text("content")
    (tmp_path / "dir1").mkdir()
    
    result = await list_directory(str(tmp_path))
    assert "[FILE] file1.txt" in result
    assert "[DIR] dir1" in result

@pytest.mark.asyncio
async def test_list_directory_caching(tmp_path):
    cache = IOCache.get_instance()
    cache.clear()
    
    (tmp_path / "cache_test.txt").write_text("content")
    
    # First call - should populate cache
    result1 = await list_directory(str(tmp_path))
    
    # Delete the file manually
    (tmp_path / "cache_test.txt").unlink()
    
    # Second call - should return cached result
    result2 = await list_directory(str(tmp_path))
    assert result1 == result2
    assert "[FILE] cache_test.txt" in result2
