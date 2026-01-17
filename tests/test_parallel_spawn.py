import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch, AsyncMock
from mcp_bridge.tools.agent_manager import get_manager

@pytest.mark.asyncio
async def test_parallel_agent_spawn():
    """Verify that multiple agents can be spawned in parallel without blocking."""
    manager = get_manager()
    
    # Mock subprocess execution to simulate a slow handshake
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(0.5)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.pid = 1234
        # Mock communicate to be async
        mock_proc.communicate = AsyncMock(return_value=(b"result", b""))
        mock_proc.wait = AsyncMock(return_value=0)
        return mock_proc

    with patch("asyncio.create_subprocess_exec", side_effect=slow_execute) as mock_exec:
        token_store = MagicMock()
        
        start_time = asyncio.get_running_loop().time()
        
        # Spawn 3 agents concurrently
        task1 = asyncio.create_task(manager.spawn_async(token_store, "task 1"))
        task2 = asyncio.create_task(manager.spawn_async(token_store, "task 2"))
        task3 = asyncio.create_task(manager.spawn_async(token_store, "task 3"))
        
        ids = await asyncio.gather(task1, task2, task3)
        
        end_time = asyncio.get_running_loop().time()
        duration = end_time - start_time
        
        # If sequential, it would be at least 1.5s (3 * 0.5s)
        # If parallel, it should be close to 0.5s
        assert duration < 1.0
        assert len(ids) == 3
        assert len(set(ids)) == 3 # All unique
