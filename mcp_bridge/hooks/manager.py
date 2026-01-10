"""
Modular Hook System for Stravinsky.
Provides interception points for tool calls and model invocations.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

try:
    from mcp_bridge.config.hook_config import is_hook_enabled
except ImportError:

    def is_hook_enabled(hook_name: str) -> bool:
        return True


logger = logging.getLogger(__name__)


class HookManager:
    """
    Manages the registration and execution of hooks.

    Hook Types:
    - pre_tool_call: Before tool execution (can modify args or block)
    - post_tool_call: After tool execution (can modify output)
    - pre_model_invoke: Before model invocation (can modify prompt/params)
    - session_idle: When session becomes idle (can inject continuation)
    - pre_compact: Before context compaction (can preserve critical context)
    """

    _instance = None

    def __init__(self):
        self.pre_tool_call_hooks: list[
            Callable[[str, dict[str, Any]], Awaitable[dict[str, Any] | None]]
        ] = []
        self.post_tool_call_hooks: list[
            Callable[[str, dict[str, Any], str], Awaitable[str | None]]
        ] = []
        self.pre_model_invoke_hooks: list[
            Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]
        ] = []
        # New hook types based on oh-my-opencode patterns
        self.session_idle_hooks: list[
            Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]
        ] = []
        self.pre_compact_hooks: list[
            Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]
        ] = []

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_pre_tool_call(
        self, hook: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any] | None]]
    ):
        """Run before a tool is called. Can modify arguments or return early result."""
        self.pre_tool_call_hooks.append(hook)

    def register_post_tool_call(
        self, hook: Callable[[str, dict[str, Any], str], Awaitable[str | None]]
    ):
        """Run after a tool call. Can modify or recover from tool output/error."""
        self.post_tool_call_hooks.append(hook)

    def register_pre_model_invoke(
        self, hook: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]
    ):
        """Run before model invocation. Can modify prompt or parameters."""
        self.pre_model_invoke_hooks.append(hook)

    def register_session_idle(
        self, hook: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]
    ):
        """Run when session becomes idle. Can inject continuation prompts."""
        self.session_idle_hooks.append(hook)

    def register_pre_compact(
        self, hook: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]
    ):
        """Run before context compaction. Can preserve critical context."""
        self.pre_compact_hooks.append(hook)

    async def execute_pre_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Executes all pre-tool call hooks."""
        current_args = arguments
        for hook in self.pre_tool_call_hooks:
            try:
                modified_args = await hook(tool_name, current_args)
                if modified_args is not None:
                    current_args = modified_args
            except Exception as e:
                logger.error(f"[HookManager] Error in pre_tool_call hook {hook.__name__}: {e}")
        return current_args

    async def execute_post_tool_call(
        self, tool_name: str, arguments: dict[str, Any], output: str
    ) -> str:
        """Executes all post-tool call hooks."""
        current_output = output
        for hook in self.post_tool_call_hooks:
            try:
                modified_output = await hook(tool_name, arguments, current_output)
                if modified_output is not None:
                    current_output = modified_output
            except Exception as e:
                logger.error(f"[HookManager] Error in post_tool_call hook {hook.__name__}: {e}")
        return current_output

    async def execute_pre_model_invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        """Executes all pre-model invoke hooks."""
        current_params = params
        for hook in self.pre_model_invoke_hooks:
            try:
                modified_params = await hook(current_params)
                if modified_params is not None:
                    current_params = modified_params
            except Exception as e:
                logger.error(f"[HookManager] Error in pre_model_invoke hook {hook.__name__}: {e}")
        return current_params

    async def execute_session_idle(self, params: dict[str, Any]) -> dict[str, Any]:
        """Executes all session idle hooks (Stop hook pattern)."""
        current_params = params
        for hook in self.session_idle_hooks:
            try:
                modified_params = await hook(current_params)
                if modified_params is not None:
                    current_params = modified_params
            except Exception as e:
                logger.error(f"[HookManager] Error in session_idle hook {hook.__name__}: {e}")
        return current_params

    async def execute_pre_compact(self, params: dict[str, Any]) -> dict[str, Any]:
        """Executes all pre-compact hooks (context preservation)."""
        current_params = params
        for hook in self.pre_compact_hooks:
            try:
                modified_params = await hook(current_params)
                if modified_params is not None:
                    current_params = modified_params
            except Exception as e:
                logger.error(f"[HookManager] Error in pre_compact hook {hook.__name__}: {e}")
        return current_params


def get_hook_manager() -> HookManager:
    return HookManager.get_instance()
