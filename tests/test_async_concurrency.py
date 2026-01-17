import pytest
import asyncio
from mcp_bridge.tools.code_search import grep_search, glob_files
from unittest.mock import patch, AsyncMock
from mcp_bridge.utils.process import ProcessResult

@pytest.mark.asyncio
async def test_concurrent_search_tools():
    """Verify that grep_search and glob_files can run concurrently."""
    
    # Mock async_execute to simulate delays
    async def delayed_execute(cmd, *args, **kwargs):
        if "rg" in cmd:
            await asyncio.sleep(0.5) # Simulate slow grep
            return ProcessResult(stdout="grep result", stderr="", returncode=0)
        elif "fd" in cmd:
            await asyncio.sleep(0.1) # Simulate fast glob
            return ProcessResult(stdout="glob result", stderr="", returncode=0)
        return ProcessResult(stdout="", stderr="", returncode=0)

    with patch("mcp_bridge.tools.code_search.async_execute", side_effect=delayed_execute) as mock_exec:
        # Run both concurrently
        start_time = asyncio.get_running_loop().time()
        
        task1 = asyncio.create_task(grep_search("pattern", "."))
        task2 = asyncio.create_task(glob_files("*.py", "."))
        
        results = await asyncio.gather(task1, task2)
        
        end_time = asyncio.get_running_loop().time()
        duration = end_time - start_time
        
        # Total time should be roughly max(0.5, 0.1) = 0.5s
        # If sequential, it would be 0.6s
        # Allow some overhead buffer
        assert duration < 0.65
        assert "grep result" in results[0]
        assert "glob result" in results[1]
