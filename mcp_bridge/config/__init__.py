# Configuration module
from .hooks import (
    get_hooks_config,
    list_hook_scripts,
    configure_hook,
    get_hook_documentation,
)

__all__ = [
    "get_hooks_config",
    "list_hook_scripts", 
    "configure_hook",
    "get_hook_documentation",
]
