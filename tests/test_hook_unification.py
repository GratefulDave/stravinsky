import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from mcp_bridge.hooks.events import EventType, HookPolicy, PolicyResult, ToolCallEvent


class MockPolicy(HookPolicy):
    @property
    def event_type(self) -> EventType:
        return EventType.POST_TOOL_CALL

    async def evaluate(self, event: ToolCallEvent) -> PolicyResult:
        if event.tool_name == "MockTool":
            return PolicyResult(
                modified_data="MODIFIED: " + (event.output or ""),
                message="MOCK MESSAGE",
                should_block=True,
                exit_code=2,
            )
        return PolicyResult(modified_data=event.output)


@pytest.mark.asyncio
async def test_mcp_adapter():
    policy = MockPolicy()
    mcp_hook = policy.as_mcp_post_hook()

    result = await mcp_hook("MockTool", {"arg1": "val1"}, "original output")
    assert result == "MODIFIED: original output"

    result = await mcp_hook("OtherTool", {}, "some output")
    assert result == "some output"


def test_native_adapter():
    policy = MockPolicy()

    # Mock stdin and stdout
    mock_input = json.dumps(
        {"tool_name": "MockTool", "tool_input": {}, "tool_response": "original output"}
    )

    with patch("sys.stdin.read", return_value=mock_input), patch(
        "sys.stdin.isatty", return_value=False
    ), patch("os.environ", {"CLAUDE_HOOK_TYPE": "PostToolUse"}), patch(
        "sys.stdout.write"
    ) as mock_stdout, patch(
        "sys.exit"
    ) as mock_exit:

                    policy.run_as_native()
        
                    # Check if sys.exit was called with 2
                    mock_exit.assert_any_call(2)
        
@pytest.mark.asyncio
async def test_tool_call_event_from_mcp():
    event = ToolCallEvent.from_mcp("TestTool", {"a": 1}, "output")
    assert event.tool_name == "TestTool"
    assert event.arguments == {"a": 1}
    assert event.output == "output"
    assert event.event_type == EventType.POST_TOOL_CALL

    event_pre = ToolCallEvent.from_mcp("TestTool", {"a": 1})
    assert event_pre.event_type == EventType.PRE_TOOL_CALL
