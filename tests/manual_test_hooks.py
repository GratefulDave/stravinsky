import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_bridge.hooks.manager import get_hook_manager
from mcp_bridge.hooks.truncator import output_truncator_hook
from mcp_bridge.hooks.edit_recovery import edit_error_recovery_hook, EDIT_RECOVERY_PROMPT
from mcp_bridge.hooks.compaction import context_compaction_hook, COMPACTION_REMINDER
from mcp_bridge.hooks.budget_optimizer import budget_optimizer_hook

async def test_truncator_hook():
    print("Testing truncator hook...")
    long_output = "a" * 20000
    result = await output_truncator_hook("test_tool", {}, long_output)
    assert result is not None
    assert len(result) < 20000
    assert "truncated" in result
    print("✅ Truncator hook passed")

async def test_edit_recovery_hook():
    print("Testing edit recovery hook...")
    error_output = "Error: oldString not found in file"
    result = await edit_error_recovery_hook("Edit", {}, error_output)
    assert result is not None
    assert EDIT_RECOVERY_PROMPT in result
    print("✅ Edit recovery hook passed")

async def test_compaction_hook():
    print("Testing compaction hook...")
    long_prompt = "p" * 150000
    params = {"prompt": long_prompt}
    result = await context_compaction_hook(params)
    assert result is not None
    assert COMPACTION_REMINDER in result["prompt"]
    print("✅ Compaction hook passed")

async def test_budget_optimizer_hook():
    print("Testing budget optimizer hook...")
    # Keyword: refactor
    params = {"model": "gemini-3-flash", "prompt": "Please refactor this", "thinking_budget": 0}
    result = await budget_optimizer_hook(params)
    assert result is not None
    assert result["thinking_budget"] == 16000
    print("✅ Budget optimizer hook passed")

async def run_all():
    await test_truncator_hook()
    await test_edit_recovery_hook()
    await test_compaction_hook()
    await test_budget_optimizer_hook()
    print("\n🚀 All manual hook tests passed!")

if __name__ == "__main__":
    asyncio.run(run_all())
