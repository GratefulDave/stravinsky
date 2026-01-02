"""
Modular Hook System for Stravinsky.
Provides interception points for tool calls and model invocations.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Awaitable

logger = logging.getLogger(__name__)

class HookManager:
    """
    Manages the registration and execution of hooks.
    """
    _instance = None

    def __init__(self):
        self.pre_tool_call_hooks: List[Callable[[str, Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]] = []
        self.post_tool_call_hooks: List[Callable[[str, Dict[str, Any], str], Awaitable[Optional[str]]]] = []
        self.pre_model_invoke_hooks: List[Callable[[Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]] = []

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_pre_tool_call(self, hook: Callable[[str, Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]):
        """Run before a tool is called. Can modify arguments or return early result."""
        self.pre_tool_call_hooks.append(hook)

    def register_post_tool_call(self, hook: Callable[[str, Dict[str, Any], str], Awaitable[Optional[str]]]):
        """Run after a tool call. Can modify or recover from tool output/error."""
        self.post_tool_call_hooks.append(hook)

    def register_pre_model_invoke(self, hook: Callable[[Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]):
        """Run before model invocation. Can modify prompt or parameters."""
        self.pre_model_invoke_hooks.append(hook)

    async def execute_pre_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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

    async def execute_post_tool_call(self, tool_name: str, arguments: Dict[str, Any], output: str) -> str:
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

    async def execute_pre_model_invoke(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

def get_hook_manager() -> HookManager:
    return HookManager.get_instance()
