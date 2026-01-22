# MCP Tool Call Injection Points - Quick Reference

## TL;DR: Where to Add Formatted Output

### CRITICAL INJECTION POINTS (Do These First)

1. **server.py, Line 313-316** - agent_spawn dispatcher
   - Add: `logger.info(f"-> agent_spawn: {emoji} {type}:{model}('{desc}')")`

2. **server.py, Line 98-141** - _format_tool_log function
   - Enhance agent_spawn case to include cost emoji and display model

3. **agent_manager.py, Line 295** - _execute_agent method
   - Add: `print(f"{emoji} SPAWNING: {type}:{model}('{desc}') ...", file=sys.stderr)`

### ALREADY DONE (No Changes Needed)

- agent_spawn output format (agent_manager.py:1050-1124) - Perfect format already
- invoke_gemini stderr (model_invoke.py:363-367) - Shows formatted message
- invoke_openai stderr (model_invoke.py:890-897) - Shows formatted message
- DelegationEnforcer integration (agent_manager.py:1072-1083) - NEW parallel enforcement

### NICE-TO-HAVE IMPROVEMENTS

4. **background_tasks.py, Line 132-137** - task_spawn function
   - Enhance return format to match agent_spawn style

5. **background_tasks.py, Line 117-127** - spawn method
   - Add stderr notification when task subprocess starts

---

## All File Paths (Absolute)

```
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/server.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/server_tools.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/agent_manager.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/model_invoke.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/background_tasks.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/code_search.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/find_code.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/semantic_search.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/search_enhancements.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/lsp/tools.py
```

---

## Complete Tool List (54 tools)

### Model Invoke (3)
| Tool | Description |
|------|-------------|
| `invoke_gemini` | Invoke Gemini model with prompt |
| `invoke_gemini_agentic` | Gemini with function calling for agentic tasks |
| `invoke_openai` | Invoke OpenAI/GPT model |

### Agents (7)
| Tool | Description |
|------|-------------|
| `agent_spawn` | Launch background agent with optional task_graph_id |
| `agent_output` | Get agent results (block=true to wait) |
| `agent_progress` | Real-time progress monitoring |
| `agent_cancel` | Cancel running agent |
| `agent_list` | List all agents |
| `agent_retry` | Retry failed agent |
| `agent_cleanup` | Remove old completed/failed agents |

### Code Search (5)
| Tool | Description |
|------|-------------|
| `ast_grep_search` | AST-aware structural pattern search |
| `ast_grep_replace` | AST-aware code replacement |
| `grep_search` | Fast text/regex search (ripgrep) |
| `glob_files` | Find files by pattern |
| `find_code` | Smart routing to optimal search strategy |

### Semantic Search (11)
| Tool | Description |
|------|-------------|
| `semantic_search` | Natural language code search |
| `hybrid_search` | Semantic + AST combined search |
| `semantic_index` | Index codebase for search |
| `semantic_stats` | Index statistics |
| `multi_query_search` | LLM-expanded query variations |
| `decomposed_search` | Break complex queries into sub-searches |
| `enhanced_search` | Auto-select best strategy |
| `start_file_watcher` | Auto-reindex on file changes |
| `stop_file_watcher` | Stop watching |
| `list_file_watchers` | List active watchers |
| `cancel_indexing` | Cancel ongoing indexing |
| `delete_index` | Remove search index |

### LSP (12)
| Tool | Description |
|------|-------------|
| `lsp_diagnostics` | File errors and warnings |
| `lsp_hover` | Type info at position |
| `lsp_goto_definition` | Jump to definition |
| `lsp_find_references` | Find all usages |
| `lsp_document_symbols` | File outline |
| `lsp_workspace_symbols` | Search symbols |
| `lsp_prepare_rename` | Validate rename |
| `lsp_rename` | Rename symbol |
| `lsp_code_actions` | Quick fixes |
| `lsp_code_action_resolve` | Apply fix |
| `lsp_extract_refactor` | Extract function |
| `lsp_servers` | List servers |

### File Operations (6)
| Tool | Description |
|------|-------------|
| `list_directory` | List files in directory |
| `read_file` | Read file contents |
| `write_file` | Write content to file |
| `replace` | Replace text in file |
| `run_shell_command` | Execute shell command |
| `tool_search` | Search for tools |

### Environment (2)
| Tool | Description |
|------|-------------|
| `get_project_context` | Git status, rules, todos |
| `get_system_health` | Dependencies and auth status |

### Sessions (3)
| Tool | Description |
|------|-------------|
| `session_list` | List Claude Code sessions |
| `session_read` | Read session messages |
| `session_search` | Search session content |

### Skills (2)
| Tool | Description |
|------|-------------|
| `skill_list` | List available commands |
| `skill_get` | Get command content |

---

## Key Imports Available

```python
from mcp_bridge.tools.agent_manager import (
    AGENT_DISPLAY_MODELS,      # agent_type -> display name
    AGENT_COST_TIERS,          # agent_type -> cost tier
    get_agent_emoji,           # agent_type -> emoji
    get_model_emoji,           # model_name -> emoji
    set_delegation_enforcer,   # Activate parallel enforcer
    clear_delegation_enforcer, # Deactivate enforcer
    get_delegation_enforcer,   # Get current enforcer
)
```

---

## Output Format Template

```
{emoji} {ACTION}: {agent_type}:{model}('{description}') {status}
task_id={task_id}
```

**Cost Tiers**:
- CHEAP = gemini-3-flash, haiku
- MEDIUM = gemini-3-pro-high
- EXPENSIVE = gpt-5.2, opus
- CLAUDE = sonnet, opus CLI

---

## Lines to Modify (Ranked by Impact)

| Priority | File | Lines | Change | Impact |
|----------|------|-------|--------|--------|
| 1 | server.py | 313-316 | Add logger.info with emoji/model | Logging visibility |
| 2 | server.py | 132-135 | Enhance _format_tool_log | Console logs |
| 3 | agent_manager.py | 295 | Add stderr print | User visibility |
| 4 | background_tasks.py | 132-137 | Enhance return format | Consistency |
| 5 | background_tasks.py | 117-127 | Add stderr notification | User feedback |

---

## NEW: DelegationEnforcer Integration

### Key Functions

```python
# Set enforcer during DELEGATE phase
set_delegation_enforcer(enforcer)

# Clear enforcer after execution
clear_delegation_enforcer()

# Get current enforcer (may be None)
enforcer = get_delegation_enforcer()
```

### agent_spawn New Parameter

```python
await agent_spawn(
    prompt="Task prompt",
    agent_type="explore",
    task_graph_id="task_001",  # NEW: Links to TaskGraph node
)
```

### Validation Logic

When `task_graph_id` is provided and enforcer is active:
1. Validates spawn is allowed by TaskGraph
2. Independent tasks MUST be spawned in parallel
3. Raises `ParallelExecutionError` if violated

---

## Validation Checklist

After implementing changes:

- [ ] agent_spawn logs show emoji + agent_type:model('desc')
- [ ] agent_spawn returns task_id= format
- [ ] Spawning agent prints to stderr immediately
- [ ] Gemini/OpenAI invocations still show stderr messages
- [ ] No import errors or circular dependencies
- [ ] All existing tests pass
- [ ] Format matches spec: {emoji} {TYPE}:{MODEL}('{DESC}') {STATUS}
- [ ] DelegationEnforcer validates parallel spawns correctly

---

## Agent Type Reference

| Agent Type | Display Model | Cost Tier |
|------------|---------------|-----------|
| explore | gemini-3-flash | CHEAP |
| dewey | gemini-3-flash | CHEAP |
| document_writer | gemini-3-flash | CHEAP |
| multimodal | gemini-3-flash | CHEAP |
| research-lead | gemini-3-flash | CHEAP |
| momus | gemini-3-flash | CHEAP |
| comment_checker | gemini-3-flash | CHEAP |
| code-reviewer | gemini-3-flash | CHEAP |
| implementation-lead | claude-sonnet-4.5 | MEDIUM |
| debugger | claude-sonnet-4.5 | MEDIUM |
| frontend | gemini-3-pro-high | MEDIUM |
| delphi | gpt-5.2 | EXPENSIVE |
| planner | opus-4.5 | EXPENSIVE |

---

## Quick Debugging

### Check if tool exists
```python
from mcp_bridge.server_tools import get_tool_definitions
tools = get_tool_definitions()
tool_names = [t.name for t in tools]
print(f"Total tools: {len(tool_names)}")
```

### Check agent configuration
```python
from mcp_bridge.tools.agent_manager import (
    AGENT_MODEL_ROUTING,
    AGENT_COST_TIERS,
    AGENT_DISPLAY_MODELS,
)
print(f"Agent types: {list(AGENT_MODEL_ROUTING.keys())}")
```

### Check enforcer status
```python
from mcp_bridge.tools.agent_manager import get_delegation_enforcer
enforcer = get_delegation_enforcer()
if enforcer:
    print(f"Enforcer active, current wave: {enforcer.get_current_wave()}")
else:
    print("No enforcer active")
```
