# Parallel Delegation Implementation - Quick Deploy Guide

**STATUS**: Foundation utilities complete (Phase 1.1-1.3 ✅). Remaining implementation below.

## Phase 1.4: Silence send_event.py (IN PROGRESS)

Replace lines 43, 47, 50 in `send_event.py` with logging:

```python
# Add at top
import logging
from pathlib import Path

# Setup logging
log_dir = Path.home() / ".claude/hooks/logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=log_dir / "event_sender.log",
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Replace lines 43-44
logging.debug(f"Server returned status: {response.status}")

# Replace lines 47-48
logging.error(f"Failed to send event: {e}")

# Replace lines 50-51
logging.error(f"Unexpected error: {e}")
```

## Phase 2: Agent Notifications (Ready to deploy)

### notification_hook.py (Refactored)

```python
#!/usr/bin/env python3
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from colors import get_agent_color, Color
from console_format import format_agent_spawn

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

def extract_agent_info(message):
    message_lower = message.lower()
    agent_type = None
    description = ""

    for agent in AGENT_DISPLAY_MODELS.keys():
        if agent == "_default":
            continue
        if agent in message_lower:
            agent_type = agent
            idx = message_lower.find(agent)
            description = message[idx + len(agent):].strip()[:80]
            break

    if not agent_type:
        return None

    description = description.strip(":-() ")
    if not description:
        description = "task delegated"

    model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])
    color_code, emoji = get_agent_color(agent_type)

    return {
        "agent_type": agent_type,
        "model": model,
        "description": description,
        "color_code": color_code,
        "emoji": emoji,
    }

def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    message = hook_input.get("message", "")
    agent_keywords = ["agent", "spawn", "delegat", "task"]
    if not any(kw in message.lower() for kw in agent_keywords):
        return 0

    agent_info = extract_agent_info(message)
    if not agent_info:
        return 0

    formatted = format_agent_spawn(
        agent_info["agent_type"],
        agent_info["model"],
        agent_info["description"],
        agent_info["color_code"],
        agent_info["emoji"]
    )
    print(formatted, file=sys.stderr)

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### tool_messaging.py (Refactored - Key Changes Only)

Add at top:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from colors import get_agent_color, colorize, Color, supports_color
from console_format import format_tool_use, format_agent_spawn
```

Replace line 243:
```python
color_code, emoji = get_agent_color(subagent_type)
formatted = format_agent_spawn(
    subagent_type,
    model,
    description,
    color_code,
    emoji
)
print(formatted, file=sys.stderr)
```

Replace line 252:
```python
formatted = format_tool_use(tool_type, server, description, emoji)
print(formatted, file=sys.stderr)
```

## Phase 3: Parallel Delegation (CRITICAL)

### dependency_tracker.py (NEW)

```python
#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

def get_project_dir():
    return Path(os.environ.get("CLAUDE_CWD", "."))

def get_dependency_graph():
    graph_file = get_project_dir() / ".claude/task_dependencies.json"
    if graph_file.exists():
        try:
            return json.loads(graph_file.read_text())
        except Exception:
            pass
    return {"dependencies": {}}

def save_dependency_graph(graph):
    graph_file = get_project_dir() / ".claude/task_dependencies.json"
    graph_file.parent.mkdir(parents=True, exist_ok=True)
    graph_file.write_text(json.dumps(graph, indent=2))

DEPENDENCY_KEYWORDS = ["after", "depends on", "requires", "once", "when", "then"]
PARALLEL_KEYWORDS = ["also", "meanwhile", "simultaneously", "and", "plus"]

def parse_todo_dependencies(todos):
    dependencies = {}
    
    for todo in todos:
        todo_id = todo.get("id")
        content = todo.get("content", "").lower()
        
        has_dependency = any(kw in content for kw in DEPENDENCY_KEYWORDS)
        is_parallel = any(kw in content for kw in PARALLEL_KEYWORDS)
        
        dependencies[todo_id] = {
            "deps": [],
            "independent": not has_dependency,
            "parallel_safe": is_parallel or not has_dependency
        }
    
    return dependencies

def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "TodoWrite":
        print(hook_input.get("prompt", ""))
        return 0

    tool_input = hook_input.get("tool_input", {})
    todos = tool_input.get("todos", [])

    graph = get_dependency_graph()
    dependencies = parse_todo_dependencies(todos)
    graph["dependencies"] = dependencies
    save_dependency_graph(graph)

    print(hook_input.get("prompt", ""))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### execution_state_tracker.py (NEW)

```python
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from datetime import datetime

def get_project_dir():
    return Path(os.environ.get("CLAUDE_CWD", "."))

def get_execution_state():
    state_file = get_project_dir() / ".claude/execution_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass
    
    return {
        "last_10_tools": [],
        "last_task_spawn_index": -1,
        "pending_todos": 0,
        "parallel_mode_active": False,
        "last_updated": None
    }

def save_execution_state(state):
    state_file = get_project_dir() / ".claude/execution_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().isoformat()
    state_file.write_text(json.dumps(state, indent=2))

def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    
    state = get_execution_state()
    state["last_10_tools"].append(tool_name)
    state["last_10_tools"] = state["last_10_tools"][-10:]
    
    if tool_name == "Task":
        try:
            index = len(state["last_10_tools"]) - 1
            state["last_task_spawn_index"] = index
        except:
            pass
    
    if tool_name == "TodoWrite":
        tool_input = hook_input.get("tool_input", {})
        todos = tool_input.get("todos", [])
        pending = sum(1 for t in todos if t.get("status") == "pending")
        state["pending_todos"] = pending
        state["parallel_mode_active"] = pending >= 2
    
    save_execution_state(state)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### parallel_reinforcement_v2.py (NEW - SMART VERSION)

```python
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"

def get_project_dir():
    return Path(os.environ.get("CLAUDE_CWD", "."))

def get_execution_state():
    state_file = get_project_dir() / ".claude/execution_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass
    return {"parallel_mode_active": False, "last_task_spawn_index": -1, "last_10_tools": [], "pending_todos": 0}

def get_dependency_graph():
    graph_file = get_project_dir() / ".claude/task_dependencies.json"
    if graph_file.exists():
        try:
            return json.loads(graph_file.read_text())
        except Exception:
            pass
    return {"dependencies": {}}

def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    prompt = hook_input.get("prompt", "")

    if not STRAVINSKY_MODE_FILE.exists():
        print(prompt)
        return 0

    state = get_execution_state()
    
    if not state.get("parallel_mode_active", False):
        print(prompt)
        return 0

    last_task_index = state.get("last_task_spawn_index", -1)
    current_index = len(state.get("last_10_tools", []))
    turns_since_task = current_index - last_task_index - 1
    
    if turns_since_task < 2:
        print(prompt)
        return 0

    graph = get_dependency_graph()
    dependencies = graph.get("dependencies", {})
    independent_tasks = [
        tid for tid, info in dependencies.items() 
        if info.get("independent", False)
    ]
    
    if len(independent_tasks) < 2:
        print(prompt)
        return 0

    reinforcement = f"""
<user-prompt-submit-hook>
[SYSTEM REMINDER - PARALLEL EXECUTION DEGRADATION DETECTED]

Analysis:
- {state.get('pending_todos', 0)} pending TODOs
- {len(independent_tasks)} independent tasks identified
- {turns_since_task} turns since last Task() spawn
- Risk: Sequential execution fallback

REQUIRED ACTION - Spawn agents for ALL independent tasks NOW:

Independent tasks: {', '.join(independent_tasks[:5])}

Pattern:
```
Task(subagent_type="explore", prompt="...", description="task_1")
Task(subagent_type="dewey", prompt="...", description="task_2")
...
```

DO NOT:
- Mark TODOs in_progress before spawning agents
- Work sequentially on one task at a time
- Use Read/Grep/Bash directly (BLOCKED in stravinsky mode)

SPAWN ALL TASK() AGENTS IN THIS SAME RESPONSE.
</user-prompt-submit-hook>

---

"""
    print(reinforcement + prompt)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Phase 3.4: Update settings.json

Add to `.claude/settings.json` under `"UserPromptSubmit"` hooks array:

```json
{
  "type": "command",
  "command": "python3 ~/.claude/hooks/parallel_reinforcement_v2.py"
}
```

Add to `"PostToolUse"` hooks (new matcher block):

```json
{
  "matcher": "*",
  "hooks": [
    {
      "type": "command",
      "command": "python3 ~/.claude/hooks/execution_state_tracker.py"
    }
  ]
},
{
  "matcher": "TodoWrite",
  "hooks": [
    {
      "type": "command",
      "command": "python3 ~/.claude/hooks/dependency_tracker.py"
    }
  ]
}
```

## Phase 4: Documentation & Cleanup

### README.md (NEW)

```markdown
# Claude Code Hooks Architecture

## Hook Execution Order

### UserPromptSubmit (5 hooks)
1. `context_monitor.py` - Track session context
2. `parallel_execution.py` - Initial ULTRAWORK mode activation
3. `parallel_reinforcement_v2.py` - **NEW** Smart adaptive reminders
4. `context.py` - Inject project context
5. `todo_continuation.py` - Resume incomplete todos

### PostToolUse
1. `truncator.py` - Truncate large outputs
2. `session_recovery.py` - Session state backup
3. `execution_state_tracker.py` - **NEW** Track tool usage patterns
4. `tool_messaging.py` - User-friendly tool notifications
5. `edit_recovery.py` - Backup edited files
6. `todo_delegation.py` - Enforce parallel after TodoWrite
7. `dependency_tracker.py` - **NEW** Parse TODO dependencies

## State Files

- `.claude/execution_state.json` - Tool usage tracking
- `.claude/task_dependencies.json` - TODO dependency graph
- `.claude/hooks/state/agent_batch.json` - Agent spawn batching
- `~/.stravinsky_mode` - Hard blocking mode marker

## Environment Variables

- `STRAVINSKY_DEBUG=1` - Enable debug output
- `STRAVINSKY_NO_COLOR=1` - Disable ANSI colors
```

## Deployment Checklist

- [x] Create utils/colors.py
- [x] Create utils/debug.py
- [x] Create utils/console_format.py
- [ ] Update send_event.py (silence debug)
- [ ] Update notification_hook.py (colors)
- [ ] Update tool_messaging.py (colors)
- [ ] Create dependency_tracker.py
- [ ] Create execution_state_tracker.py
- [ ] Create parallel_reinforcement_v2.py
- [ ] Update settings.json
- [ ] Create hooks/README.md
- [ ] Test with multi-turn session

## Expected Results

**Console Output Before**:
```
Failed to send event: Connection refused
spawned explore:gemini-3-flash('task delegated')
spawned dewey:gemini-3-flash('task delegated')
```

**Console Output After**:
```
🔵 EXPLORE → gemini-3-flash
   Task: Find all authentication implementations in codebase

🟣 DEWEY → gemini-3-flash
   Task: Research JWT best practices from official docs
```

**Parallel Delegation**: Maintained across 10+ turns with <15% sequential fallback.
