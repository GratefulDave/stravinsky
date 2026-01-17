import pytest
from mcp_bridge.hooks.manager import get_hook_manager
from mcp_bridge.hooks.events import ToolCallEvent
from mcp_bridge.hooks.truncation_policy import TruncationPolicy

@pytest.mark.asyncio
async def test_universal_truncation_applied():
    manager = get_hook_manager()
    # Ensure TruncationPolicy is registered (might be already)
    # For unit test isolation, we'll test the policy directly
    policy = TruncationPolicy(max_chars=100)
    
    # Simulate a grep_search output
    event = ToolCallEvent(
        tool_name="grep_search",
        arguments={"pattern": "test"},
        output="A" * 500
    )
    
    result = await policy.evaluate(event)
    assert "[... content truncated ...]" in result.modified_data
    assert len(result.modified_data) < 500

@pytest.mark.asyncio
async def test_read_file_skips_policy_truncation():
    # read_file handles its own truncation, so policy should skip it to avoid double-truncation
    policy = TruncationPolicy(max_chars=100)
    
    event = ToolCallEvent(
        tool_name="read_file",
        arguments={"path": "test.txt"},
        output="A" * 500
    )
    
    result = await policy.evaluate(event)
    # Should NOT be modified by the policy
    assert result.modified_data == "A" * 500
