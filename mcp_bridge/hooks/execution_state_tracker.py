"""
Execution State Tracker Hook - Track Tool Usage Patterns.

Maintains a persistent record of recent tool calls to detect patterns
and inform parallel execution decisions.

Based on GAP_ANALYSIS_PARALLEL_DELEGATION.md Option C recommendation.

Files:
- State file: ~/.stravinsky/execution_state.json
"""

from __future__ import annotations

import json
import logging
import sys
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# State file location
STATE_FILE = Path.home() / ".stravinsky" / "execution_state.json"

# Max tool history to track
MAX_TOOL_HISTORY = 20


@dataclass
class ExecutionState:
    """Tracks the current execution state for parallel delegation decisions."""

    # Recent tool calls (newest first)
    recent_tools: list[str] = field(default_factory=list)

    # Number of turns since last Task/agent_spawn call
    turns_since_agent_spawn: int = 0

    # Number of pending todos
    pending_todos: int = 0

    # Whether parallel mode is currently active (detected via /strav, ultrawork, etc.)
    parallel_mode_active: bool = False

    # Timestamp of last update
    last_updated: str = ""

    # Session ID (for multi-session tracking)
    session_id: str = "default"

    # Count of sequential patterns detected (indicates degradation)
    sequential_pattern_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionState:
        """Create from dict."""
        return cls(
            recent_tools=data.get("recent_tools", []),
            turns_since_agent_spawn=data.get("turns_since_agent_spawn", 0),
            pending_todos=data.get("pending_todos", 0),
            parallel_mode_active=data.get("parallel_mode_active", False),
            last_updated=data.get("last_updated", ""),
            session_id=data.get("session_id", "default"),
            sequential_pattern_count=data.get("sequential_pattern_count", 0),
        )


def _load_state() -> ExecutionState:
    """Load execution state from file."""
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            return ExecutionState.from_dict(data)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"[ExecutionStateTracker] Failed to load state: {e}")

    return ExecutionState()


def _save_state(state: ExecutionState) -> None:
    """Save execution state to file."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state.last_updated = datetime.now().isoformat()
        STATE_FILE.write_text(json.dumps(state.to_dict(), indent=2))
    except OSError as e:
        logger.warning(f"[ExecutionStateTracker] Failed to save state: {e}")


def record_tool_call(tool_name: str, is_agent_spawn: bool = False) -> ExecutionState:
    """
    Record a tool call in the execution history.

    Args:
        tool_name: Name of the tool that was called
        is_agent_spawn: Whether this was an agent_spawn/Task call

    Returns:
        Updated ExecutionState
    """
    state = _load_state()

    # Add to recent tools (newest first)
    state.recent_tools.insert(0, tool_name)
    state.recent_tools = state.recent_tools[:MAX_TOOL_HISTORY]

    # Update agent spawn tracking
    if is_agent_spawn:
        state.turns_since_agent_spawn = 0
        state.sequential_pattern_count = max(0, state.sequential_pattern_count - 1)
    else:
        state.turns_since_agent_spawn += 1

    # Detect sequential patterns
    # If we see TodoWrite/TodoUpdate without Task in last 3 tools, that's sequential
    if len(state.recent_tools) >= 3:
        recent_3 = [t.lower() for t in state.recent_tools[:3]]
        has_todo = any("todo" in t for t in recent_3)
        has_task = any("task" in t or "agent_spawn" in t for t in recent_3)

        if has_todo and not has_task and state.pending_todos >= 2:
            state.sequential_pattern_count += 1
            logger.info(
                f"[ExecutionStateTracker] Sequential pattern detected "
                f"(count: {state.sequential_pattern_count})"
            )

    _save_state(state)
    return state


def update_pending_todos(count: int) -> ExecutionState:
    """Update the count of pending todos."""
    state = _load_state()
    state.pending_todos = count
    _save_state(state)
    return state


def set_parallel_mode(active: bool) -> ExecutionState:
    """Set whether parallel mode is active."""
    state = _load_state()
    state.parallel_mode_active = active
    if active:
        state.sequential_pattern_count = 0  # Reset on activation
    _save_state(state)
    return state


def needs_parallel_reminder() -> tuple[bool, str | None]:
    """
    Check if a parallel execution reminder is needed.

    Returns:
        Tuple of (needs_reminder, reason)
    """
    state = _load_state()

    # Conditions that trigger a reminder:
    # 1. Parallel mode active AND 2+ pending todos AND no recent Task calls
    # 2. Sequential pattern count > 2 (degradation detected)

    if not state.parallel_mode_active:
        return False, None

    if state.pending_todos < 2:
        return False, None

    # Check for recent Task usage
    recent_5 = [t.lower() for t in state.recent_tools[:5]]
    has_recent_task = any("task" in t or "agent_spawn" in t for t in recent_5)

    if has_recent_task:
        return False, None

    # Generate reason
    if state.sequential_pattern_count >= 2:
        reason = f"Sequential pattern degradation detected ({state.sequential_pattern_count} occurrences)"
    elif state.turns_since_agent_spawn > 3:
        reason = f"No agent spawned in {state.turns_since_agent_spawn} turns"
    else:
        reason = f"{state.pending_todos} pending todos without parallel delegation"

    return True, reason


def get_state_summary() -> dict[str, Any]:
    """Get a summary of the current execution state."""
    state = _load_state()
    return {
        "recent_tools": state.recent_tools[:5],
        "turns_since_spawn": state.turns_since_agent_spawn,
        "pending_todos": state.pending_todos,
        "parallel_mode": state.parallel_mode_active,
        "sequential_patterns": state.sequential_pattern_count,
    }


async def execution_state_post_tool_hook(
    tool_name: str,
    arguments: dict[str, Any],
    output: str,
) -> str | None:
    """
    Post-tool-call hook interface for HookManager.

    Records tool usage and updates execution state.
    """
    # Determine if this is an agent spawn call
    is_agent_spawn = tool_name.lower() in [
        "task",
        "agent_spawn",
        "mcp__stravinsky__agent_spawn",
    ]

    # Record the tool call
    record_tool_call(tool_name, is_agent_spawn)

    # Update pending todos if this was a TodoWrite
    if tool_name.lower() in ["todowrite", "todo_write"]:
        todos = arguments.get("todos", [])
        pending_count = sum(1 for t in todos if t.get("status") == "pending")
        update_pending_todos(pending_count)

    # No output modification
    return None


def main():
    """CLI entry point for UserPromptSubmit hook."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    prompt = hook_input.get("prompt", "")

    # Check if parallel reminder needed
    needs_reminder, reason = needs_parallel_reminder()

    if needs_reminder and reason:
        # Get state summary for context
        summary = get_state_summary()

        reminder = f"""
[⚠️ PARALLEL EXECUTION REMINDER]

{reason}

Current state:
- Pending todos: {summary['pending_todos']}
- Turns since agent spawn: {summary['turns_since_spawn']}
- Recent tools: {', '.join(summary['recent_tools'])}

ACTION REQUIRED: Spawn Task/agent_spawn for independent pending todos NOW.
"""
        modified_prompt = reminder + "\n---\n\n" + prompt
        print(modified_prompt)
        return 0

    # No modification needed
    print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
