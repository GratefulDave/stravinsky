import pytest
from pathlib import Path
from mcp_bridge.tools.read_file import read_file

@pytest.mark.asyncio
async def test_read_normal_file(tmp_path):
    file_path = tmp_path / "test.txt"
    content = "Hello World\nLine 2"
    file_path.write_text(content)
    
    result = await read_file(str(file_path))
    assert result == content

@pytest.mark.asyncio
async def test_read_log_file_tail(tmp_path):
    log_path = tmp_path / "test.log"
    # Create a "large" log file
    lines = [f"Log line {i}" for i in range(1000)]
    log_path.write_text("\n".join(lines))
    
    # We expect it to show the END of the file by default if it's a large log
    result = await read_file(str(log_path)) 
    assert "Log line 999" in result
    assert "Log line 0" not in result
    assert "Log file detected. Reading last 100 lines by default" in result

from mcp_bridge.utils.cache import IOCache

@pytest.mark.asyncio
async def test_read_file_caching(tmp_path):
    cache = IOCache.get_instance()
    cache.clear()
    
    file_path = tmp_path / "cache_test.txt"
    file_path.write_text("initial content")
    
    # First read
    result1 = await read_file(str(file_path))
    assert result1 == "initial content"
    
    # Modify file manually
    file_path.write_text("new content")
    
    # Second read - should hit cache
    result2 = await read_file(str(file_path))
    assert result2 == "initial content"

@pytest.mark.asyncio
async def test_read_file_truncation(tmp_path):
    file_path = tmp_path / "large.txt"
    content = "A" * 50000
    file_path.write_text(content)
    
    # Universal cap should apply
    result = await read_file(str(file_path))
    assert "[Output truncated." in result
    assert len(result) < 50000
