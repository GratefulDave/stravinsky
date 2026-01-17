import pytest
import asyncio
import time
from mcp_bridge.tools.agent_manager import agent_spawn
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_event_loop_not_blocked_by_spawn():
    """Verify that spawning an agent does not block the event loop for more than 50ms."""
    
    # Mock subprocess to take some time but stay async
    async def slow_proc(*args, **kwargs):
        mock_p = MagicMock()
        mock_p.communicate = AsyncMock(return_value=(b"", b""))
        mock_p.wait = AsyncMock(return_value=0)
        mock_p.pid = 123
        return mock_p

    with patch("asyncio.create_subprocess_exec", side_effect=slow_proc):
        # Start a "heartbeat" task to measure lag
        lag_detected = False
        async def heartbeat():
            nonlocal lag_detected
            while True:
                t1 = asyncio.get_running_loop().time()
                await asyncio.sleep(0.01)
                t2 = asyncio.get_running_loop().time()
                diff = t2 - t1 - 0.01
                if diff > 0.05: # > 50ms lag
                    lag_detected = True
                await asyncio.sleep(0)

        hb_task = asyncio.create_task(heartbeat())
        
        # Spawn agent
        from unittest.mock import MagicMock
        await agent_spawn("test prompt", agent_type="explore")
        
        # Wait a bit for heartbeat to run
        await asyncio.sleep(0.1)
        
        hb_task.cancel()
        try:
            await hb_task
        except asyncio.CancelledError:
            pass
            
        assert not lag_detected, "Event loop was blocked for > 50ms during agent spawn"
