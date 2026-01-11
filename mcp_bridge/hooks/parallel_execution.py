#!/usr/bin/env python3
"""
UserPromptSubmit hook: Pre-emptive parallel execution enforcement.

Fires BEFORE response generation to inject parallel execution instructions
when implementation tasks are detected. Eliminates timing ambiguity.

CRITICAL: Also activates stravinsky mode marker when /stravinsky is invoked,
enabling hard blocking of direct tools (Read, Grep, Bash) via stravinsky_mode.py.
"""

import json
import re
import sys
from pathlib import Path

# Marker file that enables hard blocking of direct tools
STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"


def detect_stravinsky_invocation(prompt):
    """Detect if /stravinsky skill is being invoked."""
    patterns = [
        r"/stravinsky",
        r"<command-name>/stravinsky</command-name>",
        r"stravinsky orchestrator",
        r"\bultrawork\b",
    ]
    prompt_lower = prompt.lower()
    return any(re.search(p, prompt_lower) for p in patterns)


def activate_stravinsky_mode():
    """Create marker file to enable hard blocking of direct tools."""
    try:
        config = {"active": True, "reason": "invoked via /stravinsky skill"}
        STRAVINSKY_MODE_FILE.write_text(json.dumps(config))
        return True
    except OSError:
        return False


def detect_implementation_task(prompt):
    """Detect if prompt is an implementation task requiring parallel execution."""
    keywords = [
        "implement",
        "add",
        "create",
        "build",
        "refactor",
        "fix",
        "update",
        "modify",
        "change",
        "develop",
        "write code",
        "feature",
        "bug fix",
        "enhancement",
        "integrate",
    ]

    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in keywords)


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    prompt = hook_input.get("prompt", "")

    # CRITICAL: Activate stravinsky mode if /stravinsky is invoked
    # This creates the marker file that enables hard blocking of direct tools
    is_stravinsky = detect_stravinsky_invocation(prompt)
    if is_stravinsky:
        activate_stravinsky_mode()

    # Only inject for implementation tasks OR stravinsky invocation
    if not detect_implementation_task(prompt) and not is_stravinsky:
        print(prompt)
        return 0

    # Inject parallel execution instruction BEFORE prompt
    instruction = """
[🔄 PARALLEL EXECUTION MODE ACTIVE]

When you create a TodoWrite with 2+ pending items:

✅ IMMEDIATELY in THIS SAME RESPONSE (do NOT end response after TodoWrite):
   1. Spawn Task() for EACH independent pending TODO
   2. Use: Task(subagent_type="explore"|"Plan"|etc., prompt="...", description="...", run_in_background=true)
   3. Fire ALL Task calls in ONE response block
   4. Do NOT mark any TODO as in_progress until Task results return

❌ DO NOT:
   - End your response after TodoWrite
   - Mark TODOs in_progress before spawning Tasks
   - Spawn only ONE Task (spawn ALL independent tasks)
   - Wait for "next response" to spawn Tasks

Example pattern (all in SAME response):
```
TodoWrite([task1, task2, task3])
Task(subagent_type="Explore", prompt="Task 1 details", description="Task 1", run_in_background=true)
Task(subagent_type="Plan", prompt="Task 2 details", description="Task 2", run_in_background=true)
Task(subagent_type="Explore", prompt="Task 3 details", description="Task 3", run_in_background=true)
# Continue response - collect results with TaskOutput
```

---

"""

    modified_prompt = instruction + prompt
    print(modified_prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
