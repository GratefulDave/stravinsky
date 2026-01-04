"""
Hooks initialization.
Registers all Tier 1-5 hooks into the HookManager.

Hook Tiers:
- Tier 1: Post-tool-call (immediate response modification)
- Tier 2: Pre-model-invoke (context management)
- Tier 3: Pre-model-invoke (performance optimization)
- Tier 4: Pre-model-invoke (behavior enforcement)
- Tier 5: Session lifecycle (idle detection, compaction)
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
from .preemptive_compaction import preemptive_compaction_hook
from .auto_slash_command import auto_slash_command_hook
from .session_recovery import session_recovery_hook
from .empty_message_sanitizer import empty_message_sanitizer_hook

# New hooks based on oh-my-opencode patterns
from .session_idle import session_idle_hook
from .pre_compact import pre_compact_hook
from .parallel_enforcer import parallel_enforcer_post_tool_hook


def initialize_hooks():
    """Register all available hooks."""
    manager = get_hook_manager()

    # Tier 1: Post-tool-call (immediate response modification)
    manager.register_post_tool_call(output_truncator_hook)
    manager.register_post_tool_call(edit_error_recovery_hook)
    manager.register_post_tool_call(comment_checker_hook)
    manager.register_post_tool_call(agent_reminder_hook)
    manager.register_post_tool_call(session_recovery_hook)
    manager.register_post_tool_call(parallel_enforcer_post_tool_hook)  # NEW: Enforce parallel spawning

    # Tier 2: Pre-model-invoke (context management)
    manager.register_pre_model_invoke(directory_context_hook)
    manager.register_pre_model_invoke(context_compaction_hook)
    manager.register_pre_model_invoke(context_monitor_hook)
    manager.register_pre_model_invoke(preemptive_compaction_hook)
    manager.register_pre_model_invoke(empty_message_sanitizer_hook)

    # Tier 3: Pre-model-invoke (performance optimization)
    manager.register_pre_model_invoke(budget_optimizer_hook)

    # Tier 4: Pre-model-invoke (behavior enforcement)
    manager.register_pre_model_invoke(keyword_detector_hook)
    manager.register_pre_model_invoke(todo_continuation_hook)
    manager.register_pre_model_invoke(auto_slash_command_hook)

    # Tier 5: Session lifecycle hooks (NEW)
    manager.register_session_idle(session_idle_hook)  # Stop hook - idle detection
    manager.register_pre_compact(pre_compact_hook)    # PreCompact - context preservation

    return manager
