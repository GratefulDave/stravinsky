#!/usr/bin/env python3
"""
PostAssistantMessage hook: RALPH Loop (Relentless Autonomous Labor Protocol with Hardening Loop)

Automatically continues working on pending todos after assistant completes a response.
Prevents the assistant from stopping with incomplete work.

SAFETY: Maximum 10 auto-continuations per session to prevent infinite loops.

Named after the mythological Sisyphus who relentlessly pushed the boulder uphill.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


# Use CLAUDE_CWD for reliable project directory resolution
def get_project_dir() -> Path:
    """Get project directory from CLAUDE_CWD env var or fallback to cwd."""
    return Path(os.environ.get("CLAUDE_CWD", "."))


# State tracking for RALPH loop safety
RALPH_STATE_FILE = get_project_dir() / ".claude" / "ralph_state.json"


def get_ralph_state() -> dict:
    """Get current RALPH loop state."""
    if RALPH_STATE_FILE.exists():
        try:
            return json.loads(RALPH_STATE_FILE.read_text())
        except Exception:
            pass

    return {
        "continuation_count": 0,
        "last_reset": datetime.now().isoformat(),
        "max_continuations": 10,
    }


def save_ralph_state(state: dict):
    """Save RALPH loop state."""
    try:
        RALPH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        RALPH_STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def reset_ralph_state_if_needed(state: dict) -> dict:
    """Reset continuation count if last reset was >1 hour ago."""
    try:
        last_reset = datetime.fromisoformat(state.get("last_reset", datetime.now().isoformat()))
        hours_since_reset = (datetime.now() - last_reset).total_seconds() / 3600

        if hours_since_reset > 1:
            state["continuation_count"] = 0
            state["last_reset"] = datetime.now().isoformat()
    except Exception:
        pass

    return state


def get_todo_state() -> dict:
    """Get current todo state from Claude Code session or local cache."""
    todo_cache = get_project_dir() / ".claude" / "todo_state.json"

    if todo_cache.exists():
        try:
            return json.loads(todo_cache.read_text())
        except Exception:
            pass

    return {"todos": []}


def main():
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    # Get RALPH state and reset if needed
    ralph_state = get_ralph_state()
    ralph_state = reset_ralph_state_if_needed(ralph_state)

    # Safety check: prevent infinite loops
    if ralph_state["continuation_count"] >= ralph_state["max_continuations"]:
        print(
            f"\n⚠️ RALPH Loop safety limit reached ({ralph_state['max_continuations']} auto-continuations).\n",
            file=sys.stderr,
        )
        print(f"Stopping auto-continuation. Will resume on next user prompt.\n", file=sys.stderr)
        # Reset for next session
        ralph_state["continuation_count"] = 0
        ralph_state["last_reset"] = datetime.now().isoformat()
        save_ralph_state(ralph_state)
        return 0

    # Get current todo state
    todo_state = get_todo_state()
    todos = todo_state.get("todos", [])

    if not todos:
        # No todos tracked, nothing to continue
        return 0

    # Count incomplete todos
    in_progress = [t for t in todos if t.get("status") == "in_progress"]
    pending = [t for t in todos if t.get("status") == "pending"]

    if not in_progress and not pending:
        # All todos complete, reset RALPH state
        ralph_state["continuation_count"] = 0
        ralph_state["last_reset"] = datetime.now().isoformat()
        save_ralph_state(ralph_state)
        return 0

    # There are incomplete todos - trigger auto-continuation
    ralph_state["continuation_count"] += 1
    save_ralph_state(ralph_state)

    # Build continuation message
    continuation_msg = [
        "",
        "═" * 80,
        f"🔄 RALPH Loop: Auto-Continuation {ralph_state['continuation_count']}/{ralph_state['max_continuations']}",
        "═" * 80,
        "",
    ]

    if in_progress:
        continuation_msg.append(f"📌 IN_PROGRESS ({len(in_progress)} items):")
        for t in in_progress:
            continuation_msg.append(f"   • {t.get('content', 'Unknown task')}")
        continuation_msg.append("")

    if pending:
        continuation_msg.append(f"📋 PENDING ({len(pending)} items):")
        for t in pending[:5]:  # Show max 5 pending
            continuation_msg.append(f"   • {t.get('content', 'Unknown task')}")
        if len(pending) > 5:
            continuation_msg.append(f"   ... and {len(pending) - 5} more")
        continuation_msg.append("")

    continuation_msg.extend(
        [
            "⚡ CONTINUE WORKING:",
            "   1. Mark current IN_PROGRESS todo as COMPLETED if done",
            "   2. Move to next PENDING todo",
            "   3. DO NOT stop until all todos are complete",
            "",
            "═" * 80,
            "",
        ]
    )

    # Inject continuation as a system message that triggers another assistant response
    print("\n".join(continuation_msg), file=sys.stderr)

    # Return non-zero to signal that work is incomplete and should continue
    # This tells Claude Code to prompt the assistant for another response
    return 1


if __name__ == "__main__":
    sys.exit(main())
