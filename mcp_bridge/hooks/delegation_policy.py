import os
import time
from pathlib import Path

from ..utils.session_state import get_current_session_id, update_session_state
from .events import EventType, HookPolicy, PolicyResult, ToolCallEvent

# Check if stravinsky mode is active (hard blocking enabled)
STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"


def is_stravinsky_mode():
    """Check if hard blocking mode is active."""
    return STRAVINSKY_MODE_FILE.exists()


class DelegationReminderPolicy(HookPolicy):
    """
    Policy for TodoWrite: CRITICAL parallel execution enforcer.
    """

    @property
    def event_type(self) -> EventType:
        return EventType.POST_TOOL_CALL

    async def evaluate(self, event: ToolCallEvent) -> PolicyResult:
        if event.tool_name != "TodoWrite":
            return PolicyResult(modified_data=event.output)

        todos = event.arguments.get("todos", [])
        pending_count = sum(1 for t in todos if t.get("status") == "pending")

        # Update session state
        session_id = event.metadata.get("session_id") or get_current_session_id()
        update_session_state(
            {
                "last_todo_write_at": time.time(),
                "pending_todo_count": pending_count,
            },
            session_id=session_id,
        )

        if pending_count < 2:
            return PolicyResult(modified_data=event.output)

        stravinsky_active = is_stravinsky_mode()

        mode_warning = ""
        if stravinsky_active:
            mode_warning = """
⚠️ STRAVINSKY MODE ACTIVE - Direct tools (Read, Grep, Bash) are BLOCKED.
   You MUST use Task(subagent_type="explore", ...) for ALL file operations.
"""

        error_message = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                🚨 PARALLEL DELEGATION REQUIRED 🚨                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  TodoWrite created {pending_count} pending items.                                   ║
║  {mode_warning.strip()}                                                              ║
║                                                                          ║
║  You MUST spawn Task agents for ALL independent TODOs in this response.  ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  REQUIRED PATTERN:                                                       ║
║  Task(subagent_type="explore", prompt="TODO 1...", run_in_background=t)  ║
║  Task(subagent_type="explore", prompt="TODO 2...", run_in_background=t)  ║
║  ...                                                                     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
        # In PostToolUse, we often want to APPEND the reminder to the output
        new_output = (event.output or "") + "\n" + error_message

        return PolicyResult(
            modified_data=new_output,
            message=error_message,  # For native hooks, we might just print the message
            should_block=stravinsky_active,
            exit_code=2 if stravinsky_active else 1,
        )


if __name__ == "__main__":
    policy = DelegationReminderPolicy()
    policy.run_as_native()
