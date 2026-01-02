import asyncio
import pytest
from mcp_bridge.hooks.manager import get_hook_manager
from mcp_bridge.hooks.truncator import output_truncator_hook
from mcp_bridge.hooks.edit_recovery import edit_error_recovery_hook, EDIT_RECOVERY_PROMPT
from mcp_bridge.hooks.compaction import context_compaction_hook, COMPACTION_REMINDER
from mcp_bridge.hooks.directory_context import directory_context_hook
from mcp_bridge.hooks.budget_optimizer import budget_optimizer_hook

@pytest.mark.asyncio
async def test_truncator_hook():
    long_output = "a" * 20000
    result = await output_truncator_hook("test_tool", {}, long_output)
    assert result is not None
    assert len(result) < 20000
    assert "truncated" in result

@pytest.mark.asyncio
async def test_edit_recovery_hook():
    error_output = "Error: oldString not found in file"
    result = await edit_error_recovery_hook("Edit", {}, error_output)
    assert result is not None
    assert EDIT_RECOVERY_PROMPT in result

@pytest.mark.asyncio
async def test_compaction_hook():
    long_prompt = "p" * 150000
    params = {"prompt": long_prompt}
    result = await context_compaction_hook(params)
    assert result is not None
    assert COMPACTION_REMINDER in result["prompt"]

@pytest.mark.asyncio
async def test_budget_optimizer_hook():
    params = {"model": "gemini-2.0-flash-thinking", "prompt": "Please refactor and optimize this complex code", "thinking_budget": 0}
    result = await budget_optimizer_hook(params)
    assert result is not None
    assert result["thinking_budget"] == 16000

@pytest.mark.asyncio
async def test_hook_manager_integration():
    manager = get_hook_manager()
    manager.register_post_tool_call(output_truncator_hook)
    
    output = "a" * 15000
    processed = await manager.execute_post_tool_call("any_tool", {}, output)
    assert "truncated" in processed
    assert len(processed) < 15000

if __name__ == "__main__":
    asyncio.run(test_truncator_hook())
    asyncio.run(test_edit_recovery_hook())
    asyncio.run(test_compaction_hook())
    asyncio.run(test_budget_optimizer_hook())
    asyncio.run(test_hook_manager_integration())
    print("✅ All hook tests passed!")
