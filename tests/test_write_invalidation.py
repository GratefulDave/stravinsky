import pytest
import os
from pathlib import Path
from mcp_bridge.tools.read_file import read_file
from mcp_bridge.tools.write_file import write_file
from mcp_bridge.tools.replace import replace
from mcp_bridge.utils.cache import IOCache

@pytest.mark.asyncio
async def test_write_invalidates_cache(tmp_path):
    cache = IOCache.get_instance()
    cache.clear()
    
    file_path = tmp_path / "write_test.txt"
    file_path.write_text("initial")
    
    # Cache the initial content
    await read_file(str(file_path))
    assert cache.get(f"read_file:{os.path.realpath(file_path)}:0:None:20000") is not None
    
    # Write new content
    await write_file(str(file_path), "updated")
    
    # Cache should be invalidated for this path
    # (Checking prefixes or specific keys depending on implementation)
    assert cache.get(f"read_file:{os.path.realpath(file_path)}:0:None:20000") is None
    
    # Reading should return new content
    result = await read_file(str(file_path))
    assert result == "updated"

@pytest.mark.asyncio
async def test_replace_invalidates_cache(tmp_path):
    cache = IOCache.get_instance()
    cache.clear()
    
    file_path = tmp_path / "replace_test.txt"
    file_path.write_text("Hello World")
    
    # Cache it
    await read_file(str(file_path))
    
    # Replace content
    await replace(str(file_path), "Hello World", "Goodbye World", "Update greeting")
    
    # Cache should be invalidated
    assert cache.get(f"read_file:{os.path.realpath(file_path)}:0:None:20000") is None
    
    # Read back
    result = await read_file(str(file_path))
    assert result == "Goodbye World"
