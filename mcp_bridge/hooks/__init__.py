"""
Hooks initialization.
Registers all Tier 1-3 hooks into the HookManager.
"""

from .manager import get_hook_manager
from .truncator import output_truncator_hook
from .edit_recovery import edit_error_recovery_hook
from .directory_context import directory_context_hook
from .compaction import context_compaction_hook
from .budget_optimizer import budget_optimizer_hook

def initialize_hooks():
    """Register all available hooks."""
    manager = get_hook_manager()
    
    # Tier 1
    manager.register_post_tool_call(output_truncator_hook)
    manager.register_post_tool_call(edit_error_recovery_hook)
    
    # Tier 2
    manager.register_pre_model_invoke(directory_context_hook)
    manager.register_pre_model_invoke(context_compaction_hook)
    
    # Tier 3
    manager.register_pre_model_invoke(budget_optimizer_hook)

# initialize_hooks()
