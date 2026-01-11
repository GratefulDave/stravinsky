"""
Hook configuration with selective disabling support.

Provides batteries-included defaults with user-configurable overrides.
Users can disable specific hooks via ~/.stravinsky/disable_hooks.txt
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default locations for disable hooks config
DISABLE_HOOKS_PATHS = [
    Path.home() / ".stravinsky" / "disable_hooks.txt",
    Path(".stravinsky") / "disable_hooks.txt",
    Path(".claude") / "disable_hooks.txt",
]


def get_disabled_hooks() -> set[str]:
    """
    Load disabled hooks from config files.

    Checks (in order):
    1. ~/.stravinsky/disable_hooks.txt (user global)
    2. .stravinsky/disable_hooks.txt (project local)
    3. .claude/disable_hooks.txt (claude project local)

    Returns:
        Set of hook names that should be disabled.
    """
    disabled = set()

    for path in DISABLE_HOOKS_PATHS:
        if path.exists():
            try:
                content = path.read_text()
                for line in content.splitlines():
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith("#"):
                        disabled.add(line)
                logger.debug(f"Loaded disabled hooks from {path}: {disabled}")
            except Exception as e:
                logger.warning(f"Failed to read {path}: {e}")

    return disabled


def is_hook_enabled(hook_name: str) -> bool:
    """
    Check if a specific hook is enabled.

    Args:
        hook_name: Name of the hook (e.g., 'comment_checker', 'session_recovery')

    Returns:
        True if the hook is enabled (not in disable list), False otherwise.
    """
    disabled = get_disabled_hooks()
    return hook_name not in disabled


def get_hook_config_path() -> Path:
    """
    Get the path to the user's hook config directory.
    Creates it if it doesn't exist.
    """
    config_dir = Path.home() / ".stravinsky"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def create_sample_disable_hooks() -> Path | None:
    """
    Create a sample disable_hooks.txt file with documentation.

    Returns:
        Path to the created file, or None if it already exists.
    """
    config_dir = get_hook_config_path()
    disable_file = config_dir / "disable_hooks.txt"

    if disable_file.exists():
        return None

    sample_content = """# Stravinsky Hook Disabling Configuration
# Add hook names (one per line) to disable them.
# Lines starting with # are comments.
#
# Available hooks:
# ================
# 
# PreToolUse Hooks:
# - comment_checker       (checks git commit comments for quality)
# - stravinsky_mode       (blocks direct tool calls, forces delegation)
# - notification_hook     (displays agent spawn notifications)
#
# PostToolUse Hooks:
# - session_recovery      (detects API errors and logs recovery info)
# - parallel_execution    (injects parallel execution instructions)
# - todo_delegation       (enforces parallel Task spawning for todos)
# - tool_messaging        (user-friendly MCP tool messages)
# - edit_recovery         (suggests recovery for Edit failures)
# - truncator             (truncates long responses)
# - subagent_stop         (handles subagent completion)
#
# UserPromptSubmit Hooks:
# - context               (injects CLAUDE.md content)
# - todo_continuation     (reminds about incomplete todos)
#
# PreCompact Hooks:
# - pre_compact           (preserves critical context before compaction)
#
# Example - to disable the comment checker:
# comment_checker
#
# Example - to disable ultrawork mode detection:
# parallel_execution
"""

    disable_file.write_text(sample_content)
    logger.info(f"Created sample disable_hooks.txt at {disable_file}")
    return disable_file


# Hook metadata for batteries-included config
HOOK_DEFAULTS = {
    # PreToolUse hooks
    "comment_checker": {
        "type": "PreToolUse",
        "description": "Checks git commit comments for quality issues",
        "default_enabled": True,
        "exit_on_block": 0,  # Warn but don't block
    },
    "stravinsky_mode": {
        "type": "PreToolUse",
        "description": "Blocks direct tool calls, forces Task delegation",
        "default_enabled": True,
        "exit_on_block": 2,  # Hard block
    },
    "notification_hook": {
        "type": "PreToolUse",
        "description": "Displays agent spawn notifications",
        "default_enabled": True,
        "exit_on_block": 0,
    },
    # PostToolUse hooks
    "session_recovery": {
        "type": "PostToolUse",
        "description": "Detects API errors and logs recovery suggestions",
        "default_enabled": True,
        "exit_on_block": 0,
    },
    "parallel_execution": {
        "type": "PostToolUse",
        "description": "Injects parallel execution and ULTRAWORK mode",
        "default_enabled": True,
        "exit_on_block": 0,
    },
    "todo_delegation": {
        "type": "PostToolUse",
        "description": "Enforces parallel Task spawning for 2+ todos",
        "default_enabled": True,
        "exit_on_block": 2,  # Hard block in stravinsky mode
    },
    "tool_messaging": {
        "type": "PostToolUse",
        "description": "User-friendly messages for MCP tools",
        "default_enabled": True,
        "exit_on_block": 0,
    },
    "edit_recovery": {
        "type": "PostToolUse",
        "description": "Suggests recovery for Edit failures",
        "default_enabled": True,
        "exit_on_block": 0,
    },
    "truncator": {
        "type": "PostToolUse",
        "description": "Truncates responses longer than 30k chars",
        "default_enabled": True,
        "exit_on_block": 0,
    },
    "subagent_stop": {
        "type": "SubagentStop",
        "description": "Handles subagent completion events",
        "default_enabled": True,
        "exit_on_block": 0,
    },
    # UserPromptSubmit hooks
    "context": {
        "type": "UserPromptSubmit",
        "description": "Injects CLAUDE.md content to prompts",
        "default_enabled": True,
        "exit_on_block": 0,
    },
    "todo_continuation": {
        "type": "UserPromptSubmit",
        "description": "Reminds about incomplete todos",
        "default_enabled": True,
        "exit_on_block": 0,
    },
    # PreCompact hooks
    "pre_compact": {
        "type": "PreCompact",
        "description": "Preserves critical context before compaction",
        "default_enabled": True,
        "exit_on_block": 0,
    },
}


def get_enabled_hooks() -> dict:
    """
    Get all enabled hooks with their configuration.

    Returns:
        Dict of hook_name -> hook_config for enabled hooks only.
    """
    disabled = get_disabled_hooks()
    enabled = {}

    for hook_name, config in HOOK_DEFAULTS.items():
        if hook_name not in disabled and config.get("default_enabled", True):
            enabled[hook_name] = config

    return enabled


def list_hooks() -> str:
    """
    List all hooks with their status.

    Returns:
        Formatted string showing hook status.
    """
    disabled = get_disabled_hooks()
    lines = ["# Stravinsky Hooks Status", ""]

    for hook_name, config in sorted(HOOK_DEFAULTS.items()):
        status = "DISABLED" if hook_name in disabled else "enabled"
        icon = "" if hook_name in disabled else ""
        lines.append(f"{icon} {hook_name}: {status} - {config['description']}")

    return "\n".join(lines)
