#!/usr/bin/env python3
"""
UserPromptSubmit hook: Pre-emptive parallel execution enforcement.

Fires BEFORE response generation to inject parallel execution instructions
when implementation tasks are detected. Eliminates timing ambiguity.

CRITICAL: Also activates stravinsky mode marker when /stravinsky is invoked,
enabling hard blocking of direct tools (Read, Grep, Bash) via stravinsky_mode.py.

ULTRAWORK MODE (oh-my-opencode parity):
When "ultrawork" is detected in prompt (case insensitive):
- Injects aggressive parallelization instructions
- Forces maximum agent concurrency
- Enables 32k thinking budget guidance
- All async agents fire immediately
"""

import json
import os
import sys
import re
from pathlib import Path

# Marker file that enables hard blocking of direct tools
STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"

# ULTRAWORK mode pattern for aggressive parallel execution
ULTRAWORK_PATTERN = r"\bultrawork\b"


# Use CLAUDE_CWD for reliable project directory resolution
def get_project_dir() -> Path:
    """Get project directory from CLAUDE_CWD env var or fallback to cwd."""
    return Path(os.environ.get("CLAUDE_CWD", "."))


# Marker file that indicates MCP skill execution context (project-scoped)
MCP_MODE_MARKER_NAME = ".stravinsky/mcp_mode"


def detect_ultrawork_mode(prompt):
    """Detect if ULTRAWORK mode is requested for maximum parallel execution."""
    prompt_lower = prompt.lower()
    return bool(re.search(ULTRAWORK_PATTERN, prompt_lower))


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
    except IOError:
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


def get_ultrawork_instruction():
    """Return the aggressive ULTRAWORK mode instruction injection."""
    return """
<ultrawork-mode>

**MANDATORY**: You MUST say "ULTRAWORK MODE ENABLED!" to the user as your first response when this mode activates. This is non-negotiable.

[CODE RED] Maximum precision required. Ultrathink before acting.

YOU MUST LEVERAGE ALL AVAILABLE AGENTS TO THEIR FULLEST POTENTIAL.
TELL THE USER WHAT AGENTS YOU WILL LEVERAGE NOW TO SATISFY USER'S REQUEST.

## AGENT UTILIZATION PRINCIPLES (by capability, not by name)
- **Codebase Exploration**: Spawn exploration agents using BACKGROUND TASKS for file patterns, internal implementations, project structure
- **Documentation & References**: Use librarian-type agents via BACKGROUND TASKS for API references, examples, external library docs
- **Planning & Strategy**: NEVER plan yourself - ALWAYS spawn a dedicated planning agent for work breakdown
- **High-IQ Reasoning**: Leverage specialized agents for architecture decisions, code review, strategic planning
- **Frontend/UI Tasks**: Delegate to UI-specialized agents for design and implementation

## EXECUTION RULES
- **TODO**: Track EVERY step. Mark complete IMMEDIATELY after each.
- **PARALLEL**: Fire independent agent calls simultaneously via background_task - NEVER wait sequentially.
- **BACKGROUND FUWT**: Use background_task for exploration/research agents (10+ concurrent if needed).
- **VERIFY**: Re-read request after completion. Check ALL requirements met before reporting done.
- **DELEGATE**: Don't do everything yourself - orchestrate specialized agents for their strengths.

## WORKFLOW
1. Analyze the request and identify required capabilities
2. Spawn exploration/librarian agents via background_task in PARALLEL (10+ if needed)
3. Always Use Plan agent with gathered context to create detailed work breakdown
4. Execute with continuous verification against original requirements

## VERIFICATION GUARANTEE (NON-NEGOTIABLE)

**NOTHING is "done" without PROOF it works.**

### Pre-Implementation: Define Success Criteria

BEFORE writing ANY code, you MUST define:

| Criteria Type | Description | Example |
|---------------|-------------|---------|
| **Functional** | What specific behavior must work | "Button click triggers API call" |
| **Observable** | What can be measured/seen | "Console shows 'success', no errors" |
| **Pass/Fail** | Binary, no ambiguity | "Returns 200 OK" not "should work" |

Write these criteria explicitly. Share with user if scope is non-trivial.

## ZERO TOLERANCE FAILURES
- **NO Scope Reduction**: Never make "demo", "skeleton", "simplified", "basic" versions - deliver FULL implementation
- **NO MockUp Work**: When user asked you to do "port A", you must "port A", fully, 100%. No Extra feature, No reduced feature, no mock data, fully working 100% port.
- **NO Partial Completion**: Never stop at 60-80% saying "you can extend this..." - finish 100%
- **NO Assumed Shortcuts**: Never skip requirements you deem "optional" or "can be added later"
- **NO Premature Stopping**: Never declare done until ALL TODOs are completed and verified
- **NO TEST DELETION**: Never delete or skip failing tests to make the build pass. Fix the code, not the tests.

THE USER ASKED FOR X. DELIVER EXACTLY X. NOT A SUBSET. NOT A DEMO. NOT A STARTING POINT.

</ultrawork-mode>

---

"""


def get_parallel_instruction():
    """Return the standard parallel execution instruction."""
    return """
<user-prompt-submit-hook>
[🔄 PARALLEL EXECUTION MODE ACTIVE]

When you create a TodoWrite with 2+ pending items:

✅ IMMEDIATELY in THIS SAME RESPONSE (do NOT end response after TodoWrite):
   1. Spawn Task() for EACH independent pending TODO
   2. Use: Task(subagent_type="explore"|"dewey"|"code-reviewer"|etc., prompt="...", description="...")
   3. Fire ALL Task calls in ONE response block
   4. Do NOT mark any TODO as in_progress until Task results return

❌ DO NOT:
   - End your response after TodoWrite
   - Mark TODOs in_progress before spawning agents
   - Spawn only ONE agent (spawn ALL independent tasks)
   - Wait for "next response" to spawn agents
   - Use Read/Grep/Bash for exploratory work (use explore agents)

**Exploratory queries (NO TodoWrite needed):**
For "Find X", "Explain where Y", "Search for Z" → SKIP TodoWrite, spawn agents immediately:
```
Task(subagent_type="explore", prompt="Find X...", description="Find X")
Task(subagent_type="explore", prompt="Find Y...", description="Find Y")
# Continue response - synthesize results
```

**Implementation tasks (TodoWrite + agents):**
```
TodoWrite([task1, task2, task3])
Task(subagent_type="explore", prompt="Task 1 details", description="Task 1")
Task(subagent_type="dewey", prompt="Task 2 details", description="Task 2")
Task(subagent_type="code-reviewer", prompt="Task 3 details", description="Task 3")
# Continue response - synthesize results from Task tool responses
```
</user-prompt-submit-hook>

---

"""


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

    # Check for ULTRAWORK mode - maximum parallel execution
    is_ultrawork = detect_ultrawork_mode(prompt)

    # Only inject for implementation tasks, stravinsky invocation, or ULTRAWORK
    if not detect_implementation_task(prompt) and not is_stravinsky and not is_ultrawork:
        print(prompt)
        return 0

    # Select instruction based on mode
    if is_ultrawork:
        # ULTRAWORK mode: aggressive parallelization + verification
        instruction = get_ultrawork_instruction()
    else:
        # Standard parallel execution mode
        instruction = get_parallel_instruction()

    modified_prompt = instruction + prompt
    print(modified_prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
