#!/usr/bin/env python3
"""
UserPromptSubmit hook: Todo Continuation Enforcer

Checks if there are incomplete todos (in_progress or pending) and injects
a reminder to continue working on them before starting new work.

Aligned with oh-my-opencode's [SYSTEM REMINDER - TODO CONTINUATION] pattern.
"""

import json
import os
import sys
from pathlib import Path


def get_todo_state() -> dict:
    """Try to get current todo state from Claude Code session or local cache."""
    # Claude Code stores todo state - we can check via session files
    # For now, we'll use a simple file-based approach
    cwd = Path(os.environ.get("CLAUDE_CWD", "."))
    todo_cache = cwd / ".claude" / "todo_state.json"

    if todo_cache.exists():
        try:
            return json.loads(todo_cache.read_text())
        except Exception:
            pass

    return {"todos": []}


def main():
    try:
        data = json.load(sys.stdin)
        prompt = data.get("prompt", "")
    except Exception:
        return 0

    # Get current todo state
    state = get_todo_state()
    todos = state.get("todos", [])

    if not todos:
        # No todos tracked, pass through
        print(prompt)
        return 0

    # Count incomplete todos
    in_progress = [t for t in todos if t.get("status") == "in_progress"]
    pending = [t for t in todos if t.get("status") == "pending"]

    if not in_progress and not pending:
        # All todos complete, pass through
        print(prompt)
        return 0

    # Build AGGRESSIVE reminder with RALPH loop activation
    reminder_parts = [
        "",
        "=" * 80,
        "🔄 RALPH LOOP: INCOMPLETE WORK DETECTED",
        "=" * 80,
        "",
    ]

    if in_progress:
        reminder_parts.append(f"📌 IN_PROGRESS ({len(in_progress)} items):")
        for t in in_progress:
            reminder_parts.append(f"   • {t.get('content', 'Unknown task')}")
        reminder_parts.append("")

    if pending:
        reminder_parts.append(f"📋 PENDING ({len(pending)} items):")
        for t in pending[:5]:  # Show max 5 pending
            reminder_parts.append(f"   • {t.get('content', 'Unknown task')}")
        if len(pending) > 5:
            reminder_parts.append(f"   ... and {len(pending) - 5} more")
        reminder_parts.append("")

    reminder_parts.extend(
        [
            "⚡ MANDATORY CONTINUATION PROTOCOL:",
            "",
            "YOU MUST CONTINUE WORKING IMMEDIATELY. DO NOT WAIT FOR USER INPUT.",
            "",
            "1. If IN_PROGRESS todo exists → Complete it NOW",
            "2. If blocked → Explain why and mark as pending, move to next",
            "3. Pick next PENDING todo → Mark as in_progress → Execute",
            "4. Repeat until ALL todos are completed",
            "",
            "🚫 DO NOT:",
            '   - Ask user "Should I continue?" (YES, ALWAYS CONTINUE)',
            "   - Wait for user confirmation (CONTINUE AUTOMATICALLY)",
            "   - Stop with pending work (COMPLETE EVERYTHING)",
            "   - Start new work before finishing todos (FINISH FIRST)",
            "",
            "THIS IS AN AUTO-CONTINUATION. PROCEED IMMEDIATELY.",
            "",
            "=" * 80,
            "",
        ]
    )

    reminder = "\n".join(reminder_parts)
    print(reminder + prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
