#!/usr/bin/env python3
"""
Stravinsky Hook Installer

Installs Stravinsky hooks to ~/.claude/hooks/ directory and updates settings.json.
Hooks provide enhanced Claude Code behavior including:
- Parallel execution enforcement
- Tool output truncation
- Edit error recovery
- Context injection
- Todo continuation
- Tool messaging
- Stravinsky mode (orchestrator blocking)
- Notification handling
- Subagent completion tracking
- Pre-compaction context preservation
"""

import json
import sys
from pathlib import Path

# Hook file contents - these will be written to ~/.claude/hooks/
HOOKS = {
    "truncator.py": """import os
import sys
import json

MAX_CHARS = 30000

def main():
    try:
        data = json.load(sys.stdin)
        tool_response = data.get("tool_response", "")
    except Exception:
        return

    if len(tool_response) > MAX_CHARS:
        header = f"[TRUNCATED - {len(tool_response)} chars reduced to {MAX_CHARS}]\\n"
        footer = "\\n...[TRUNCATED]"
        truncated = tool_response[:MAX_CHARS]
        print(header + truncated + footer)
    else:
        print(tool_response)

if __name__ == "__main__":
    main()
""",
    "edit_recovery.py": '''#!/usr/bin/env python3
"""Edit error recovery hook - detects edit failures and forces file reading."""
import json
import os
import sys

EDIT_ERROR_PATTERNS = [
    "oldString and newString must be different",
    "oldString not found",
    "oldString found multiple times",
    "Target content not found",
    "Multiple occurrences of target content found",
]

def main():
    try:
        data = json.load(sys.stdin)
        tool_response = data.get("tool_response", "")
    except Exception:
        return 0

    # Check for edit errors
    is_edit_error = any(pattern in tool_response for pattern in EDIT_ERROR_PATTERNS)
    
    if is_edit_error:
        error_msg = """
> **[EDIT ERROR - IMMEDIATE ACTION REQUIRED]**
> You made an Edit mistake. STOP and do this NOW:
> 1. **READ** the file immediately to see its ACTUAL current state.
> 2. **VERIFY** what the content really looks like (your assumption was wrong).
> 3. **APOLOGIZE** briefly to the user for the error.
> 4. **CONTINUE** with corrected action based on the real file content.
> **DO NOT** attempt another edit until you've read and verified the file state.
"""
        print(tool_response + error_msg)
    else:
        print(tool_response)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
''',
    "context.py": """import os
import sys
import json
from pathlib import Path

def main():
    try:
        data = json.load(sys.stdin)
        prompt = data.get("prompt", "")
    except Exception:
        return

    cwd = Path(os.environ.get("CLAUDE_CWD", "."))
    
    # Files to look for
    context_files = ["AGENTS.md", "README.md", "CLAUDE.md"]
    found_context = ""

    for f in context_files:
        path = cwd / f
        if path.exists():
            try:
                content = path.read_text()
                found_context += f"\\n\\n--- LOCAL CONTEXT: {f} ---\\n{content}\\n"
                break # Only use one for brevity
            except Exception:
                pass

    if found_context:
        # Prepend context to prompt
        # We wrap the user prompt to distinguish it
        new_prompt = f"{found_context}\\n\\n[USER PROMPT]\\n{prompt}"
        print(new_prompt)
    else:
        print(prompt)

if __name__ == "__main__":
    main()
""",
    "parallel_execution.py": '''#!/usr/bin/env python3
"""
UserPromptSubmit hook: Pre-emptive parallel execution enforcement.

Fires BEFORE response generation to inject parallel execution instructions
when implementation tasks are detected. Eliminates timing ambiguity.

CRITICAL: Also activates stravinsky mode marker when /stravinsky is invoked,
enabling hard blocking of direct tools (Read, Grep, Bash) via stravinsky_mode.py.
"""
import json
import sys
import re
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
    except IOError:
        return False


def detect_implementation_task(prompt):
    """Detect if prompt is an implementation task requiring parallel execution."""
    keywords = [
        'implement', 'add', 'create', 'build', 'refactor', 'fix',
        'update', 'modify', 'change', 'develop', 'write code',
        'feature', 'bug fix', 'enhancement', 'integrate'
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
''',
    "todo_continuation.py": '''#!/usr/bin/env python3
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

    # Build reminder
    reminder_parts = ["[SYSTEM REMINDER - TODO CONTINUATION]", ""]

    if in_progress:
        reminder_parts.append(f"IN PROGRESS ({len(in_progress)} items):")
        for t in in_progress:
            reminder_parts.append(f"  - {t.get('content', 'Unknown task')}")
        reminder_parts.append("")

    if pending:
        reminder_parts.append(f"PENDING ({len(pending)} items):")
        for t in pending[:5]:  # Show max 5 pending
            reminder_parts.append(f"  - {t.get('content', 'Unknown task')}")
        if len(pending) > 5:
            reminder_parts.append(f"  ... and {len(pending) - 5} more")
        reminder_parts.append("")

    reminder_parts.extend([
        "IMPORTANT: You have incomplete work. Before starting anything new:",
        "1. Continue working on IN_PROGRESS todos first",
        "2. If blocked, explain why and move to next PENDING item",
        "3. Only start NEW work if all todos are complete or explicitly abandoned",
        "",
        "---",
        "",
    ])

    reminder = "\\n".join(reminder_parts)
    print(reminder + prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
    "todo_delegation.py": '''#!/usr/bin/env python3
"""
PostToolUse hook for TodoWrite: CRITICAL parallel execution enforcer.

This hook fires AFTER TodoWrite completes. If there are 2+ pending items,
it outputs a STRONG reminder that Task agents must be spawned immediately.

Exit code 2 is used to signal a HARD BLOCK - Claude should see this as
a failure condition requiring immediate correction.

Works in tandem with:
- parallel_execution.py (UserPromptSubmit): Pre-emptive instruction injection
- stravinsky_mode.py (PreToolUse): Hard blocking of Read/Grep/Bash tools
"""
import json
import sys
from pathlib import Path

# Check if stravinsky mode is active (hard blocking enabled)
STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"


def is_stravinsky_mode():
    """Check if hard blocking mode is active."""
    return STRAVINSKY_MODE_FILE.exists()


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")

    if tool_name != "TodoWrite":
        return 0

    # Get the todos that were just written
    tool_input = hook_input.get("tool_input", {})
    todos = tool_input.get("todos", [])

    # Count pending todos
    pending_count = sum(1 for t in todos if t.get("status") == "pending")

    if pending_count < 2:
        return 0

    # Check if stravinsky mode is active
    stravinsky_active = is_stravinsky_mode()

    # CRITICAL: Output urgent reminder for parallel Task spawning
    mode_warning = ""
    if stravinsky_active:
        mode_warning = """
⚠️ STRAVINSKY MODE ACTIVE - Direct tools (Read, Grep, Bash) are BLOCKED.
   You MUST use Task(subagent_type="explore", ...) for ALL file operations.
"""

    error_message = f"""
🚨 PARALLEL DELEGATION REQUIRED 🚨

TodoWrite created {pending_count} pending items.
{mode_warning}
You MUST spawn Task agents for ALL independent TODOs in THIS SAME RESPONSE.

Required pattern (IMMEDIATELY after this message):
Task(subagent_type="explore", prompt="TODO 1...", description="TODO 1", run_in_background=true)
Task(subagent_type="explore", prompt="TODO 2...", description="TODO 2", run_in_background=true)
...

DO NOT:
- End your response without spawning Tasks
- Mark TODOs in_progress before spawning Tasks
- Use Read/Grep/Bash directly (BLOCKED in stravinsky mode)

Your NEXT action MUST be multiple Task() calls, one for each independent TODO.
"""
    print(error_message, file=sys.stderr)

    # Exit code 2 = HARD BLOCK in stravinsky mode
    # Exit code 1 = WARNING otherwise
    return 2 if stravinsky_active else 1


if __name__ == "__main__":
    sys.exit(main())
''',
    "stravinsky_mode.py": '''#!/usr/bin/env python3
"""
Stravinsky Mode Enforcer Hook

This PreToolUse hook blocks native file reading tools (Read, Search, Grep, Bash)
when stravinsky orchestrator mode is active, forcing use of Task tool for native
subagent delegation.

Stravinsky mode is activated by creating a marker file:
  ~/.stravinsky_mode

The /stravinsky command should create this file, and it should be
removed when the task is complete.

Exit codes:
  0 = Allow the tool to execute
  2 = Block the tool (reason sent via stderr)
"""

import json
import os
import sys
from pathlib import Path

# Marker file that indicates stravinsky mode is active
STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"

# Tools to block when in stravinsky mode
BLOCKED_TOOLS = {
    "Read",
    "Search",
    "Grep",
    "Bash",
    "MultiEdit",
    "Edit",
}

# Tools that are always allowed
ALLOWED_TOOLS = {
    "TodoRead",
    "TodoWrite",
    "Task",  # Native subagent delegation
    "Agent",  # MCP agent tools
}

# Agent routing recommendations
AGENT_ROUTES = {
    "Read": "explore",
    "Grep": "explore",
    "Search": "explore",
    "Bash": "explore",
    "Edit": "code-reviewer",
    "MultiEdit": "code-reviewer",
}


def is_stravinsky_mode_active() -> bool:
    """Check if stravinsky orchestrator mode is active."""
    return STRAVINSKY_MODE_FILE.exists()


def read_stravinsky_mode_config() -> dict:
    """Read the stravinsky mode configuration if it exists."""
    if not STRAVINSKY_MODE_FILE.exists():
        return {}
    try:
        return json.loads(STRAVINSKY_MODE_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return {"active": True}


def main():
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # If we can't parse input, allow the tool
        sys.exit(0)

    tool_name = hook_input.get("toolName", hook_input.get("tool_name", ""))
    params = hook_input.get("params", {})

    # Always allow certain tools
    if tool_name in ALLOWED_TOOLS:
        sys.exit(0)

    # Check if stravinsky mode is active
    if not is_stravinsky_mode_active():
        # Not in stravinsky mode, allow all tools
        sys.exit(0)

    config = read_stravinsky_mode_config()

    # Check if this tool should be blocked
    if tool_name in BLOCKED_TOOLS:
        # Determine which agent to delegate to
        agent = AGENT_ROUTES.get(tool_name, "explore")

        # Get tool context for better messaging
        context = ""
        if tool_name == "Grep":
            pattern = params.get("pattern", "")
            context = f" (searching for '{pattern[:30]}')"
        elif tool_name == "Read":
            file_path = params.get("file_path", "")
            context = f" (reading {os.path.basename(file_path)})" if file_path else ""

        # User-friendly delegation message
        print(f"🎭 {agent}('Delegating {tool_name}{context}')", file=sys.stderr)

        # Block the tool and tell Claude why
        reason = f"""⚠️ STRAVINSKY MODE ACTIVE - {tool_name} BLOCKED

You are in Stravinsky orchestrator mode. Native tools are disabled.

Instead of using {tool_name}, you MUST use Task tool for native subagent delegation:
  - Task(subagent_type="explore", ...) for file reading/searching
  - Task(subagent_type="dewey", ...) for documentation research
  - Task(subagent_type="code-reviewer", ...) for code analysis
  - Task(subagent_type="debugger", ...) for error investigation
  - Task(subagent_type="frontend", ...) for UI/UX work
  - Task(subagent_type="delphi", ...) for strategic architecture decisions

Example:
  Task(
    subagent_type="explore",
    prompt="Read and analyze the authentication module",
    description="Analyze auth"
  )

To exit stravinsky mode, run:
  rm ~/.stravinsky_mode
"""
        # Send reason to stderr (Claude sees this)
        print(reason, file=sys.stderr)
        # Exit with code 2 to block the tool
        sys.exit(2)

    # Tool not in block list, allow it
    sys.exit(0)


if __name__ == "__main__":
    main()
''',
    "tool_messaging.py": '''#!/usr/bin/env python3
"""
PostToolUse hook for user-friendly tool messaging.

Outputs concise messages about which agent/tool was used and what it did.
Format examples:
- ast-grep('Searching for authentication patterns')
- delphi:openai/gpt-5.2-medium('Analyzing architecture trade-offs')
- explore:gemini-3-flash('Finding all API endpoints')
"""

import json
import os
import sys

# Agent model mappings
AGENT_MODELS = {
    "explore": "gemini-3-flash",
    "dewey": "gemini-3-flash",
    "code-reviewer": "sonnet",
    "debugger": "sonnet",
    "frontend": "gemini-3-pro-high",
    "delphi": "gpt-5.2-medium",
}

# Tool display names
TOOL_NAMES = {
    "mcp__stravinsky__ast_grep_search": "ast-grep",
    "mcp__stravinsky__grep_search": "grep",
    "mcp__stravinsky__glob_files": "glob",
    "mcp__stravinsky__lsp_diagnostics": "lsp-diagnostics",
    "mcp__stravinsky__lsp_hover": "lsp-hover",
    "mcp__stravinsky__lsp_goto_definition": "lsp-goto-def",
    "mcp__stravinsky__lsp_find_references": "lsp-find-refs",
    "mcp__stravinsky__lsp_document_symbols": "lsp-symbols",
    "mcp__stravinsky__lsp_workspace_symbols": "lsp-workspace-symbols",
    "mcp__stravinsky__invoke_gemini": "gemini",
    "mcp__stravinsky__invoke_openai": "openai",
    "mcp__grep-app__searchCode": "grep.app",
    "mcp__grep-app__github_file": "github-file",
}


def extract_description(tool_name: str, params: dict) -> str:
    """Extract a concise description of what the tool did."""

    # AST-grep
    if "ast_grep" in tool_name:
        pattern = params.get("pattern", "")
        directory = params.get("directory", ".")
        return f"Searching AST in {directory} for '{pattern[:40]}...'"

    # Grep/search
    if "grep_search" in tool_name or "searchCode" in tool_name:
        pattern = params.get("pattern", params.get("query", ""))
        return f"Searching for '{pattern[:40]}...'"

    # Glob
    if "glob_files" in tool_name:
        pattern = params.get("pattern", "")
        return f"Finding files matching '{pattern}'"

    # LSP diagnostics
    if "lsp_diagnostics" in tool_name:
        file_path = params.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else "file"
        return f"Checking {filename} for errors"

    # LSP hover
    if "lsp_hover" in tool_name:
        file_path = params.get("file_path", "")
        line = params.get("line", "")
        filename = os.path.basename(file_path) if file_path else "file"
        return f"Type info for {filename}:{line}"

    # LSP goto definition
    if "lsp_goto" in tool_name:
        file_path = params.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else "symbol"
        return f"Finding definition in {filename}"

    # LSP find references
    if "lsp_find_references" in tool_name:
        file_path = params.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else "symbol"
        return f"Finding all references to symbol in {filename}"

    # LSP symbols
    if "lsp_symbols" in tool_name or "lsp_document_symbols" in tool_name:
        file_path = params.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else "file"
        return f"Getting symbols from {filename}"

    if "lsp_workspace_symbols" in tool_name:
        query = params.get("query", "")
        return f"Searching workspace for symbol '{query}'"

    # Gemini invocation
    if "invoke_gemini" in tool_name:
        prompt = params.get("prompt", "")
        # Extract first meaningful line
        first_line = prompt.split('\\n')[0][:50] if prompt else "Processing"
        return first_line

    # OpenAI invocation
    if "invoke_openai" in tool_name:
        prompt = params.get("prompt", "")
        first_line = prompt.split('\\n')[0][:50] if prompt else "Strategic analysis"
        return first_line

    # GitHub file fetch
    if "github_file" in tool_name:
        path = params.get("path", "")
        repo = params.get("repo", "")
        return f"Fetching {path} from {repo}"

    # Task delegation
    if tool_name == "Task":
        subagent_type = params.get("subagent_type", "unknown")
        description = params.get("description", "")
        model = AGENT_MODELS.get(subagent_type, "unknown")
        return f"{subagent_type}:{model}('{description}')"

    return "Processing"


def main():
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        tool_name = hook_input.get("toolName", hook_input.get("tool_name", ""))
        params = hook_input.get("params", hook_input.get("tool_input", {}))

        # Only output messages for MCP tools and Task delegations
        if not (tool_name.startswith("mcp__") or tool_name == "Task"):
            sys.exit(0)

        # Get tool display name
        display_name = TOOL_NAMES.get(tool_name, tool_name)

        # Special handling for Task delegations
        if tool_name == "Task":
            subagent_type = params.get("subagent_type", "unknown")
            description = params.get("description", "")
            model = AGENT_MODELS.get(subagent_type, "unknown")

            # Show full agent delegation message
            print(f"🎯 {subagent_type}:{model}('{description}')", file=sys.stderr)
        else:
            # Regular tool usage
            description = extract_description(tool_name, params)
            print(f"🔧 {display_name}('{description}')", file=sys.stderr)

        sys.exit(0)

    except Exception as e:
        # On error, fail silently (don't disrupt workflow)
        print(f"Tool messaging hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
''',
    "notification_hook.py": '''#!/usr/bin/env python3
"""
Notification hook for agent spawn messages.

Fires on Notification events to output user-friendly messages about
which agent was spawned, what model it uses, and what task it's doing.

Format: spawned {agent_type}:{model}('{description}')
Example: spawned delphi:gpt-5.2-medium('Debug xyz code')
"""

import json
import sys
from typing import Optional, Dict, Any


# Agent display model mappings
AGENT_DISPLAY_MODELS = {
    "explore": "gemini-3-flash",
    "dewey": "gemini-3-flash",
    "document_writer": "gemini-3-flash",
    "multimodal": "gemini-3-flash",
    "frontend": "gemini-3-pro-high",
    "delphi": "gpt-5.2-medium",
    "planner": "opus-4.5",
    "code-reviewer": "sonnet-4.5",
    "debugger": "sonnet-4.5",
    "_default": "sonnet-4.5",
}


def extract_agent_info(message: str) -> Optional[Dict[str, str]]:
    """
    Extract agent spawn information from notification message.

    Looks for patterns like:
    - "Agent explore spawned for task..."
    - "Spawned delphi agent: description"
    - Task tool delegation messages
    """
    message_lower = message.lower()

    # Try to extract agent type from message
    agent_type = None
    description = ""

    for agent in AGENT_DISPLAY_MODELS.keys():
        if agent == "_default":
            continue
        if agent in message_lower:
            agent_type = agent
            # Extract description after agent name
            idx = message_lower.find(agent)
            description = message[idx + len(agent):].strip()[:60]
            break

    if not agent_type:
        return None

    # Clean up description
    description = description.strip(":-() ")
    if not description:
        description = "task delegated"

    display_model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])

    return {
        "agent_type": agent_type,
        "model": display_model,
        "description": description,
    }


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    # Get notification message
    message = hook_input.get("message", "")
    notification_type = hook_input.get("notification_type", "")

    # Only process agent-related notifications
    agent_keywords = ["agent", "spawn", "delegat", "task"]
    if not any(kw in message.lower() for kw in agent_keywords):
        return 0

    # Extract agent info
    agent_info = extract_agent_info(message)
    if not agent_info:
        return 0

    # Format and output
    output = f"spawned {agent_info['agent_type']}:{agent_info['model']}('{agent_info['description']}')"
    print(output, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
    "subagent_stop.py": '''#!/usr/bin/env python3
"""
SubagentStop hook: Handler for agent/subagent completion events.

Fires when a Claude Code subagent (Task tool) finishes to:
1. Output completion status messages
2. Verify agent produced expected output
3. Block completion if critical validation fails
4. Integrate with TODO tracking

Exit codes:
  0 = Allow completion
  2 = Block completion (force continuation)
"""

import json
import sys
from pathlib import Path
from typing import Optional, Tuple


STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"


def is_stravinsky_mode() -> bool:
    """Check if stravinsky mode is active."""
    return STRAVINSKY_MODE_FILE.exists()


def extract_subagent_info(hook_input: dict) -> Tuple[str, str, str]:
    """
    Extract subagent information from hook input.

    Returns: (agent_type, description, status)
    """
    # Try to get from tool parameters or response
    params = hook_input.get("tool_input", hook_input.get("params", {}))
    response = hook_input.get("tool_response", "")

    agent_type = params.get("subagent_type", "unknown")
    description = params.get("description", "")[:50]

    # Determine status from response
    status = "completed"
    response_lower = response.lower() if isinstance(response, str) else ""
    if "error" in response_lower or "failed" in response_lower:
        status = "failed"
    elif "timeout" in response_lower:
        status = "timeout"

    return agent_type, description, status


def format_completion_message(agent_type: str, description: str, status: str) -> str:
    """Format user-friendly completion message."""
    icon = "✓" if status == "completed" else "✗"
    return f"{icon} Subagent {agent_type} {status}: {description}"


def should_block(status: str, agent_type: str) -> bool:
    """
    Determine if we should block completion.

    Block if:
    - Agent failed AND stravinsky mode active AND critical agent type
    """
    if status != "completed" and is_stravinsky_mode():
        critical_agents = {"delphi", "code-reviewer", "debugger"}
        if agent_type in critical_agents:
            return True
    return False


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    # Extract subagent info
    agent_type, description, status = extract_subagent_info(hook_input)

    # Output completion message
    message = format_completion_message(agent_type, description, status)
    print(message, file=sys.stderr)

    # Check if we should block
    if should_block(status, agent_type):
        print(f"\\n⚠️ CRITICAL SUBAGENT FAILURE - {agent_type} failed", file=sys.stderr)
        print("Review the error and retry or delegate to delphi.", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
    "pre_compact.py": '''#!/usr/bin/env python3
"""
PreCompact hook: Context preservation before compaction.

Fires before Claude Code compacts conversation context to:
1. Preserve critical context patterns
2. Maintain stravinsky mode state
3. Warn about information loss
4. Save state for recovery

Cannot block compaction (exit 2 only shows error).
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"
STATE_DIR = Path.home() / ".claude" / "state"
COMPACTION_LOG = STATE_DIR / "compaction.jsonl"

# Patterns to preserve
PRESERVE_PATTERNS = [
    "ARCHITECTURE:",
    "DESIGN DECISION:",
    "CONSTRAINT:",
    "REQUIREMENT:",
    "MUST NOT:",
    "NEVER:",
    "CRITICAL ERROR:",
    "CURRENT TASK:",
    "BLOCKED BY:",
    "[STRAVINSKY MODE]",
    "PARALLEL_DELEGATION:",
]


def ensure_state_dir():
    """Ensure state directory exists."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_stravinsky_mode_state() -> Dict[str, Any]:
    """Read stravinsky mode state."""
    if not STRAVINSKY_MODE_FILE.exists():
        return {"active": False}
    try:
        content = STRAVINSKY_MODE_FILE.read_text().strip()
        return json.loads(content) if content else {"active": True}
    except (json.JSONDecodeError, IOError):
        return {"active": True}


def extract_preserved_context(prompt: str) -> List[str]:
    """Extract context matching preservation patterns."""
    preserved = []
    lines = prompt.split("\\n")

    for i, line in enumerate(lines):
        for pattern in PRESERVE_PATTERNS:
            if pattern in line:
                # Capture line + 2 more for context
                context = "\\n".join(lines[i:min(i+3, len(lines))])
                preserved.append(context)
                break

    return preserved[:15]  # Max 15 items


def log_compaction(preserved: List[str], stravinsky_active: bool):
    """Log compaction event for audit."""
    ensure_state_dir()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "preserved_count": len(preserved),
        "stravinsky_mode": stravinsky_active,
        "preview": [p[:50] for p in preserved[:3]],
    }

    try:
        with COMPACTION_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\\n")
    except IOError:
        pass


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    prompt = hook_input.get("prompt", "")
    trigger = hook_input.get("trigger", "auto")

    # Get stravinsky mode state
    strav_state = get_stravinsky_mode_state()
    stravinsky_active = strav_state.get("active", False)

    # Extract preserved context
    preserved = extract_preserved_context(prompt)

    # Log compaction event
    log_compaction(preserved, stravinsky_active)

    # Output preservation warning
    if preserved or stravinsky_active:
        print(f"\\n[PreCompact] Context compaction triggered ({trigger})", file=sys.stderr)
        print(f"  Preserved items: {len(preserved)}", file=sys.stderr)
        if stravinsky_active:
            print("  [STRAVINSKY MODE ACTIVE] - State will persist", file=sys.stderr)
        print("  Audit log: ~/.claude/state/compaction.jsonl", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
}


# Hook registration configuration for settings.json
# IMPORTANT: Uses ~/.claude/hooks/ (global) paths so hooks work in ANY project
HOOK_REGISTRATIONS = {
    "Notification": [
        {
            "matcher": "*",
            "hooks": [
                {"type": "command", "command": "python3 ~/.claude/hooks/notification_hook.py"}
            ],
        }
    ],
    "SubagentStop": [
        {
            "matcher": "*",
            "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/subagent_stop.py"}],
        }
    ],
    "PreCompact": [
        {
            "matcher": "*",
            "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/pre_compact.py"}],
        }
    ],
    "PreToolUse": [
        {
            "matcher": "Read,Search,Grep,Bash,Edit,MultiEdit",
            "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/stravinsky_mode.py"}],
        }
    ],
    "UserPromptSubmit": [
        {
            "matcher": "*",
            "hooks": [
                {"type": "command", "command": "python3 ~/.claude/hooks/parallel_execution.py"},
                {"type": "command", "command": "python3 ~/.claude/hooks/context.py"},
                {"type": "command", "command": "python3 ~/.claude/hooks/todo_continuation.py"},
            ],
        }
    ],
    "PostToolUse": [
        {
            "matcher": "*",
            "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/truncator.py"}],
        },
        {
            "matcher": "mcp__stravinsky__*,mcp__grep-app__*,Task",
            "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/tool_messaging.py"}],
        },
        {
            "matcher": "Edit,MultiEdit",
            "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/edit_recovery.py"}],
        },
        {
            "matcher": "TodoWrite",
            "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/todo_delegation.py"}],
        },
    ],
}


def install_hooks():
    """Install Stravinsky hooks to ~/.claude/hooks/"""

    # Get home directory
    home = Path.home()
    claude_dir = home / ".claude"
    hooks_dir = claude_dir / "hooks"
    settings_file = claude_dir / "settings.json"

    print("🚀 Stravinsky Hook Installer")
    print("=" * 60)

    # Create hooks directory if it doesn't exist
    if not hooks_dir.exists():
        print(f"📁 Creating hooks directory: {hooks_dir}")
        hooks_dir.mkdir(parents=True, exist_ok=True)
    else:
        print(f"📁 Hooks directory exists: {hooks_dir}")

    # Install each hook file
    print(f"\\n📝 Installing {len(HOOKS)} hook files...")
    for filename, content in HOOKS.items():
        hook_path = hooks_dir / filename
        print(f"  ✓ {filename}")
        hook_path.write_text(content)
        hook_path.chmod(0o755)  # Make executable

    # Merge hook registrations into settings.json
    print("\\n⚙️  Updating settings.json...")

    # Load existing settings or create new
    if settings_file.exists():
        print(f"  📖 Reading existing settings: {settings_file}")
        with settings_file.open("r") as f:
            settings = json.load(f)
    else:
        print(f"  📝 Creating new settings file: {settings_file}")
        settings = {}

    # Merge hooks configuration
    if "hooks" not in settings:
        settings["hooks"] = {}

    for hook_type, registrations in HOOK_REGISTRATIONS.items():
        settings["hooks"][hook_type] = registrations
        print(f"  ✓ Registered {hook_type} hooks")

    # Write updated settings
    with settings_file.open("w") as f:
        json.dump(settings, f, indent=2)

    print("\\n✅ Installation complete!")
    print("=" * 60)
    print("\\n📋 Installed hooks:")
    for filename in HOOKS:
        print(f"  • {filename}")

    print("\\n🔧 Hook types registered:")
    for hook_type in HOOK_REGISTRATIONS:
        print(f"  • {hook_type}")

    print(f"\\n📁 Installation directory: {hooks_dir}")
    print(f"⚙️  Settings file: {settings_file}")
    print("\\n🎉 Stravinsky hooks are now active!")
    print("\\n💡 Tip: Run '/stravinsky' to activate orchestrator mode")

    return 0


def main():
    """CLI entry point."""
    try:
        return install_hooks()
    except Exception as e:
        print(f"\\n❌ Installation failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
