"""
Hooks initialization.
Registers all Tier 1-4 hooks into the HookManager.
"""

from .manager import get_hook_manager
from .truncator import output_truncator_hook
from .edit_recovery import edit_error_recovery_hook
from .directory_context import directory_context_hook
from .compaction import context_compaction_hook
from .budget_optimizer import budget_optimizer_hook
from .todo_enforcer import todo_continuation_hook
from .keyword_detector import keyword_detector_hook
from .comment_checker import comment_checker_hook
from .context_monitor import context_monitor_hook
from .agent_reminder import agent_reminder_hook


def initialize_hooks():
    """Register all available hooks."""
    manager = get_hook_manager()

    # Tier 1: Post-tool-call (immediate response modification)
    manager.register_post_tool_call(output_truncator_hook)
    manager.register_post_tool_call(edit_error_recovery_hook)
    manager.register_post_tool_call(comment_checker_hook)
    manager.register_post_tool_call(agent_reminder_hook)

    # Tier 2: Pre-model-invoke (context management)
    manager.register_pre_model_invoke(directory_context_hook)
    manager.register_pre_model_invoke(context_compaction_hook)
    manager.register_pre_model_invoke(context_monitor_hook)

    # Tier 3: Pre-model-invoke (performance optimization)
    manager.register_pre_model_invoke(budget_optimizer_hook)

    # Tier 4: Pre-model-invoke (behavior enforcement)
    manager.register_pre_model_invoke(keyword_detector_hook)
    manager.register_pre_model_invoke(todo_continuation_hook)
