import pytest
import asyncio
from mcp_bridge.utils.process import async_execute, ProcessResult

@pytest.mark.asyncio
async def test_async_execute_success():
    cmd = ["echo", "hello world"]
    result = await async_execute(cmd)
    assert result.returncode == 0
    assert result.stdout.strip() == "hello world"
    assert result.stderr == ""

@pytest.mark.asyncio
async def test_async_execute_timeout():
    # Sleep for 2 seconds, but timeout is 0.5s
    cmd = ["sleep", "2"]
    with pytest.raises(asyncio.TimeoutError):
        await async_execute(cmd, timeout=0.5)

@pytest.mark.asyncio
async def test_async_execute_error():
    # Command that fails
    cmd = ["ls", "/nonexistent/path"]
    result = await async_execute(cmd)
    assert result.returncode != 0
    assert "No such file" in result.stderr or "ls:" in result.stderr

@pytest.mark.asyncio
async def test_async_execute_cwd(tmp_path):
    # Verify working directory
    marker = tmp_path / "marker.txt"
    marker.touch()
    
    cmd = ["ls", "marker.txt"]
    result = await async_execute(cmd, cwd=str(tmp_path))
    assert result.returncode == 0
    assert "marker.txt" in result.stdout
