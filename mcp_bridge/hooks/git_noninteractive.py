"""
Git Non-Interactive Environment Hook.

Prevents git interactive command hangs by prepending environment variables.
"""

import logging
import re
import shlex
from typing import Any

logger = logging.getLogger(__name__)

# Patterns for banned interactive git commands
BANNED_INTERACTIVE_PATTERNS = [
    r"git\s+add\s+.*-p",  # git add -p (patch mode)
    r"git\s+add\s+.*--patch",
    r"git\s+commit\s+.*-v",  # git commit -v (verbose with diff)
    r"git\s+rebase\s+.*-i",  # git rebase -i (interactive)
    r"git\s+rebase\s+.*--interactive",
    r"git\s+add\s+.*-i",  # git add -i (interactive)
    r"git\s+add\s+.*--interactive",
    r"git\s+checkout\s+.*-p",  # git checkout -p (patch mode)
    r"git\s+reset\s+.*-p",  # git reset -p (patch mode)
]

# Environment variables to set for non-interactive git
NON_INTERACTIVE_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_EDITOR": "true",  # No-op editor
    "GIT_PAGER": "cat",  # No paging
}


def escape_shell_arg(arg: str) -> str:
    """
    Escape shell argument for safe injection.
    """
    # Use shlex.quote for proper escaping
    return shlex.quote(arg)


async def git_noninteractive_hook(
    tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any] | None:
    """
    Pre-tool-call hook that prepends non-interactive env vars to git commands.

    Detects interactive git commands and either:
    1. Warns and blocks them (if highly interactive like -i)
    2. Prepends env vars to make them non-interactive
    """
    # Only process Bash tool
    if tool_name != "Bash":
        return None

    command = arguments.get("command", "")
    if not command or "git" not in command.lower():
        return None

    # Check for banned interactive patterns
    for pattern in BANNED_INTERACTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            logger.warning(
                f"[GitNonInteractive] Detected interactive git command: {pattern}"
            )
            # Add warning to command output
            warning = (
                f"\n[WARNING] Interactive git command detected: {command}\n"
                f"This may hang. Consider using non-interactive alternatives.\n"
            )
            # Don't block, just warn - user might know what they're doing
            return None

    # Prepend environment variables to make git non-interactive
    if "git" in command.lower():
        env_prefix = " ".join(
            [f"{k}={escape_shell_arg(v)}" for k, v in NON_INTERACTIVE_ENV.items()]
        )
        modified_command = f"{env_prefix} {command}"

        logger.info("[GitNonInteractive] Prepending non-interactive env vars to git command")

        # Return modified arguments
        modified_args = arguments.copy()
        modified_args["command"] = modified_command
        return modified_args

    return None
