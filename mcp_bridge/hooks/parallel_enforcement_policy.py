import os
import time

from ..utils.session_state import get_current_session_id, get_session_state, update_session_state
from .events import EventType, HookPolicy, PolicyResult, ToolCallEvent


class ParallelEnforcementPolicy(HookPolicy):
    """
    Policy to enforce parallel delegation after TodoWrite.
    Warns if the agent tries to use direct tools instead of Task agents
    when multiple TODOs are pending.
    """

    @property
    def event_type(self) -> EventType:
        return EventType.PRE_TOOL_CALL

    async def evaluate(self, event: ToolCallEvent) -> PolicyResult:
        # We don't block agent_spawn or Task themselves
        if event.tool_name in ["agent_spawn", "task_spawn", "Task"]:
            return PolicyResult(modified_data=event.arguments)

        session_id = event.metadata.get("session_id") or get_current_session_id()
        state = get_session_state(session_id)

        last_write = state.get("last_todo_write_at", 0)
        pending_count = state.get("pending_todo_count", 0)

        # If TodoWrite was recent (last 60 seconds) and multiple tasks are pending
        if time.time() - last_write < 60 and pending_count >= 2:
            # Check if this tool is allowed
            allowed_tools = ["Read", "read_file", "ls", "list_directory"]
            
            # If it's a direct action tool (Bash, Edit, etc.), warn
            if event.tool_name not in allowed_tools:
                message = f"""
┌──────────────────────────────────────────────────────────────────────────┐
│                ⚠️  SEQUENTIAL EXECUTION DETECTED  ⚠️                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  You have {pending_count} pending tasks from your last TodoWrite.                   │
│  You are currently attempting to use '{event.tool_name}' directly.             │
│                                                                          │
│  To maintain high performance and parallel workflow:                     │
│  1. You SHOULD have spawned Task agents for all independent tasks.       │
│  2. Direct tool use is discouraged when multiple tasks are pending.      │
│                                                                          │
│  If these tasks are truly independent, please use Task() instead.        │
└──────────────────────────────────────────────────────────────────────────┘
"""
                # Increment warning count
                attempts = state.get("blocked_sequential_attempts", 0) + 1
                update_session_state({"blocked_sequential_attempts": attempts}, session_id=session_id)
                
                return PolicyResult(
                    modified_data=event.arguments,
                    message=message,
                    # We could block here if attempts > threshold
                )

        return PolicyResult(modified_data=event.arguments)


if __name__ == "__main__":
    policy = ParallelEnforcementPolicy()
    policy.run_as_native()
