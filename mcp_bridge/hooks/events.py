"""
Unified Event Model and Policy Base for Stravinsky Hooks.
Enables code sharing between native Claude Code hooks and MCP bridge hooks.
"""

import asyncio
import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EventType(Enum):
    PRE_TOOL_CALL = "pre_tool_call"
    POST_TOOL_CALL = "post_tool_call"
    PRE_MODEL_INVOKE = "pre_model_invoke"
    SESSION_IDLE = "session_idle"
    PRE_COMPACT = "pre_compact"
    NOTIFICATION = "notification"
    SUBAGENT_STOP = "subagent_stop"


@dataclass
class ToolCallEvent:
    tool_name: str
    arguments: dict[str, Any]
    output: str | None = None
    event_type: EventType = EventType.PRE_TOOL_CALL
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mcp(
        cls, tool_name: str, arguments: dict[str, Any], output: str | None = None
    ) -> "ToolCallEvent":
        event_type = EventType.POST_TOOL_CALL if output is not None else EventType.PRE_TOOL_CALL
        return cls(tool_name=tool_name, arguments=arguments, output=output, event_type=event_type)

    @classmethod
    def from_native(cls) -> Optional["ToolCallEvent"]:
        """Parses ToolCallEvent from stdin (Native Claude Code hook pattern)."""
        try:
            # Native hooks often get input via stdin
            if sys.stdin.isatty():
                return None

            raw_input = sys.stdin.read()
            if not raw_input:
                return None

            data = json.loads(raw_input)
            # print(f"DEBUG: raw_data={data}", file=sys.stderr)

            # Claude Code native hook input varies by type
            tool_name = data.get("tool_name") or data.get("toolName", "")
            arguments = data.get("tool_input") or data.get("params", {})
            output = data.get("output") or data.get("tool_response")

            # Infer event type from env or data
            import os
            native_type = os.environ.get("CLAUDE_HOOK_TYPE", "")

            # print(f"DEBUG: native_type={native_type}, output={output}", file=sys.stderr)

            event_type = EventType.PRE_TOOL_CALL
            if "PostToolUse" in native_type or output is not None:
                event_type = EventType.POST_TOOL_CALL
            elif "PreCompact" in native_type:
                event_type = EventType.PRE_COMPACT
            elif "Notification" in native_type:
                event_type = EventType.NOTIFICATION
            elif "SubagentStop" in native_type:
                event_type = EventType.SUBAGENT_STOP

            return cls(
                tool_name=tool_name,
                arguments=arguments,
                output=output,
                event_type=event_type,
                metadata=data,
            )
        except Exception:
            return None


@dataclass
class PolicyResult:
    """
    The result of a policy evaluation.
    """

    modified_data: Any | None = None
    should_block: bool = False
    message: str | None = None
    exit_code: int = 0


class HookPolicy(ABC):
    """
    Abstract Base Class for unified hook policies.
    """

    @property
    @abstractmethod
    def event_type(self) -> EventType:
        """The event type this policy responds to."""
        pass

    @abstractmethod
    async def evaluate(self, event: ToolCallEvent) -> PolicyResult:
        """
        Evaluate the policy and return a PolicyResult.
        """
        pass

    def as_mcp_pre_hook(self):
        """Wraps the policy for HookManager.register_pre_tool_call."""

        async def pre_hook(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
            event = ToolCallEvent.from_mcp(tool_name, arguments)
            result = await self.evaluate(event)
            return result.modified_data

        return pre_hook

    def as_mcp_post_hook(self):
        """Wraps the policy for HookManager.register_post_tool_call."""

        async def post_hook(tool_name: str, arguments: dict[str, Any], output: str) -> str | None:
            event = ToolCallEvent.from_mcp(tool_name, arguments, output)
            result = await self.evaluate(event)
            return result.modified_data

        return post_hook

    def run_as_native(self):
        """Entry point for running the policy as a standalone script."""
        event = ToolCallEvent.from_native()
        if not event:
            sys.exit(0)

        # Allow policies to respond to multiple event types if they want,
        # but default to strict matching.
        if hasattr(self, "supported_event_types"):
            if event.event_type not in self.supported_event_types:
                sys.exit(0)
        elif event.event_type != self.event_type:
            sys.exit(0)

        result = asyncio.run(self.evaluate(event))

        if result.message:
            # Print message to stdout for Claude to see
            print(result.message)

        if result.should_block:
            sys.exit(result.exit_code or 2)

        sys.exit(0)
