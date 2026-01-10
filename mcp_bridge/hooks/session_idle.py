"""
Session Idle Hook - Stop Hook Implementation.

Detects when session becomes idle with incomplete todos and injects
a continuation prompt to force task completion.

Based on oh-my-opencode's todo-continuation-enforcer pattern.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Continuation prompt injected when session is idle with incomplete todos
TODO_CONTINUATION_PROMPT = """
[SYSTEM REMINDER - TODO CONTINUATION]

You have incomplete tasks in your todo list. Continue working on the next pending task.

RULES:
- Proceed immediately without asking for permission
- Mark the current task as in_progress before starting
- Mark each task complete when finished
- Do NOT stop until all tasks are done
- If blocked, create a new task describing what needs to be resolved

STATUS CHECK:
Use TodoWrite to check your current task status and continue with the next pending item.
"""

# Track sessions to prevent duplicate injections
_idle_sessions: dict[str, bool] = {}
_last_activity: dict[str, float] = {}


async def session_idle_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Pre-model-invoke hook that detects idle sessions with incomplete todos.

    Checks if:
    1. The conversation has pending todos
    2. The session has been idle (no recent tool calls)
    3. A continuation hasn't already been injected

    If all conditions met, injects TODO_CONTINUATION_PROMPT.
    """
    import time

    prompt = params.get("prompt", "")
    session_id = params.get("session_id", "default")

    # Skip if already contains continuation reminder
    if "[SYSTEM REMINDER - TODO CONTINUATION]" in prompt:
        return None

    # Skip if this is a fresh prompt (user just typed something)
    if params.get("is_user_message", False):
        _last_activity[session_id] = time.time()
        _idle_sessions[session_id] = False
        return None

    # Check for pending todos in the prompt/context
    has_pending_todos = _detect_pending_todos(prompt)

    if not has_pending_todos:
        return None

    # Check idle threshold (2 seconds of no activity)
    current_time = time.time()
    last_activity = _last_activity.get(session_id, current_time)
    idle_seconds = current_time - last_activity

    if idle_seconds < 2.0:
        return None

    # Check if already injected for this idle period
    if _idle_sessions.get(session_id, False):
        return None

    # Mark as injected and inject continuation
    _idle_sessions[session_id] = True
    logger.info(f"[SessionIdleHook] Injecting TODO continuation for session {session_id}")

    modified_prompt = prompt + "\n\n" + TODO_CONTINUATION_PROMPT

    return {**params, "prompt": modified_prompt}


def _detect_pending_todos(prompt: str) -> bool:
    """
    Detect if there are pending todos in the conversation.

    Looks for patterns like:
    - [pending] or status: pending
    - TodoWrite with pending items
    - Incomplete task lists
    """
    pending_patterns = [
        "[pending]",
        "status: pending",
        '"status": "pending"',
        "pending tasks",
        "incomplete tasks",
        "remaining todos",
    ]

    prompt_lower = prompt.lower()
    return any(pattern.lower() in prompt_lower for pattern in pending_patterns)


def reset_session(session_id: str = "default"):
    """Reset idle state for a session (call when user provides new input)."""
    _idle_sessions[session_id] = False
    import time
    _last_activity[session_id] = time.time()
