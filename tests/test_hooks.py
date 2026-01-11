import asyncio
import pytest
from mcp_bridge.hooks.manager import get_hook_manager
from mcp_bridge.hooks.compaction import context_compaction_hook, COMPACTION_REMINDER
from mcp_bridge.hooks.directory_context import directory_context_hook
from mcp_bridge.hooks.budget_optimizer import budget_optimizer_hook

# Note: edit_recovery and truncator hooks have been converted to CLI-only scripts
# and no longer export async functions for testing

@pytest.mark.asyncio
async def test_compaction_hook():
    long_prompt = "p" * 150000
    params = {"prompt": long_prompt}
    result = await context_compaction_hook(params)
    assert result is not None
    assert COMPACTION_REMINDER in result["prompt"]

@pytest.mark.asyncio
async def test_budget_optimizer_hook():
    params = {"model": "gemini-3-flash", "prompt": "Please refactor and optimize this complex code", "thinking_budget": 0}
    result = await budget_optimizer_hook(params)
    assert result is not None
    assert result["thinking_budget"] == 16000

if __name__ == "__main__":
    asyncio.run(test_compaction_hook())
    asyncio.run(test_budget_optimizer_hook())
    print("✅ All hook tests passed!")
