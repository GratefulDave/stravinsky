"""
Interactive Bash Session Hook (Tmux Manager).

Manages persistent tmux sessions and cleanup.
"""

import logging
import shlex
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# Track tmux sessions created by Stravinsky
_tracked_sessions: set[str] = set()
SESSION_PREFIX = "stravinsky-"


def parse_tmux_command(command: str) -> str | None:
    """
    Parse tmux command to extract session name.

    Handles quote/escape properly using shlex.
    """
    try:
        # Use shlex to properly parse quoted arguments
        parts = shlex.split(command)

        # Look for tmux new-session or attach-session
        if "tmux" not in parts:
            return None

        # Find session name after -t or -s flags
        for i, part in enumerate(parts):
            if part in ["-s", "-t"] and i + 1 < len(parts):
                session_name = parts[i + 1]
                return normalize_session_name(session_name)

        # Check for inline session name (tmux new -s name)
        for i, part in enumerate(parts):
            if part == "new" or part == "new-session":
                # Look for -s in following parts
                for j in range(i + 1, len(parts)):
                    if parts[j] == "-s" and j + 1 < len(parts):
                        return normalize_session_name(parts[j + 1])

    except Exception as e:
        logger.error(f"[TmuxManager] Failed to parse tmux command: {e}")
        return None

    return None


def normalize_session_name(name: str) -> str:
    """
    Normalize tmux session name (strip window/pane suffixes).

    Examples:
      "session:0" -> "session"
      "session:window.pane" -> "session"
    """
    # Split on : to remove window/pane references
    return name.split(":")[0]


async def tmux_manager_hook(
    tool_name: str, tool_input: dict[str, Any], tool_output: str | None = None
) -> str | None:
    """
    Post-tool-call hook that tracks tmux sessions.

    Monitors Bash tool for tmux commands and tracks session names.
    """
    # Only process Bash tool
    if tool_name != "Bash":
        return None

    command = tool_input.get("command", "")
    if not command or "tmux" not in command:
        return None

    # Parse session name from tmux command
    session_name = parse_tmux_command(command)

    if session_name:
        # Track with Stravinsky prefix
        if not session_name.startswith(SESSION_PREFIX):
            session_name = SESSION_PREFIX + session_name

        _tracked_sessions.add(session_name)
        logger.info(f"[TmuxManager] Tracking tmux session: {session_name}")

        # Append reminder about active sessions
        if tool_output:
            reminder = f"\n\n[TMUX SESSION] Active session tracked: {session_name}\n" \
                       f"Cleanup on session end: kill-session -t {session_name}"
            return tool_output + reminder

    return tool_output


def cleanup_tmux_sessions() -> list[str]:
    """
    Kill all tracked tmux sessions.

    Returns list of killed session names.
    """
    killed = []

    for session_name in _tracked_sessions:
        try:
            # Kill tmux session
            subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            killed.append(session_name)
            logger.info(f"[TmuxManager] Killed tmux session: {session_name}")

        except FileNotFoundError:
            logger.warning("[TmuxManager] tmux command not found")
            break
        except subprocess.TimeoutExpired:
            logger.warning(f"[TmuxManager] Timeout killing session: {session_name}")
        except Exception as e:
            logger.error(f"[TmuxManager] Failed to kill session {session_name}: {e}")

    # Clear tracked sessions
    _tracked_sessions.clear()

    return killed


def get_tracked_sessions() -> set[str]:
    """
    Get set of currently tracked tmux sessions.
    """
    return _tracked_sessions.copy()
