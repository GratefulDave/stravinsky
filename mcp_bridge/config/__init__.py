# Configuration module
from .hooks import (
    configure_hook,
    get_hook_documentation,
    get_hooks_config,
    list_hook_scripts,
)

__all__ = [
    "get_hooks_config",
    "list_hook_scripts", 
    "configure_hook",
    "get_hook_documentation",
]
