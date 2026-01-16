# MCP Tool Call Injection Points - Quick Reference

## TL;DR: Where to Add Formatted Output

### CRITICAL INJECTION POINTS (Do These First)

1. **server.py, Line 313-316** - agent_spawn dispatcher
   - Add: `logger.info(f"→ agent_spawn: {emoji} {type}:{model}('{desc}')")`
   
2. **server.py, Line 98-141** - _format_tool_log function
   - Enhance agent_spawn case to include cost emoji and display model
   
3. **agent_manager.py, Line 295** - _execute_agent method
   - Add: `print(f"{emoji} SPAWNING: {type}:{model}('{desc}') ...", file=sys.stderr)`

### ALREADY DONE (No Changes Needed)

- ✅ agent_spawn output format (agent_manager.py:915-916) - Perfect format already
- ✅ invoke_gemini stderr (model_invoke.py:363-367) - Shows formatted message
- ✅ invoke_openai stderr (model_invoke.py:890-897) - Shows formatted message

### NICE-TO-HAVE IMPROVEMENTS

4. **background_tasks.py, Line 132-137** - task_spawn function
   - Enhance return format to match agent_spawn style
   
5. **background_tasks.py, Line 117-127** - spawn method
   - Add stderr notification when task subprocess starts

---

## All File Paths (Absolute)

```
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/server.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/agent_manager.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/model_invoke.py
/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/background_tasks.py
```

---

## Key Imports Available

```python
from .tools.agent_manager import (
    AGENT_DISPLAY_MODELS,      # agent_type -> display name
    AGENT_COST_TIERS,          # agent_type -> cost tier
    get_agent_emoji,           # agent_type -> emoji
    get_model_emoji,           # model_name -> emoji
)
```

---

## Output Format Template

```
{emoji} {ACTION}: {agent_type}:{model}('{description}') {status}
task_id={task_id}
```

**Emojis**:
- 🟢 = Cheap (gemini-3-flash, haiku)
- 🔵 = Medium (gemini-3-pro-high)
- 🟣 = Expensive (gpt-5.2, opus)
- 🟠 = Claude (sonnet, opus CLI)
- 🔮 = Gemini invoked
- 🧠 = OpenAI invoked
- ⏳ = Spawned, waiting

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

## Validation Checklist

After implementing changes:

- [ ] agent_spawn logs show emoji + agent_type:model('desc')
- [ ] agent_spawn returns task_id= format
- [ ] Spawning agent prints to stderr immediately
- [ ] Gemini/OpenAI invocations still show stderr messages
- [ ] No import errors or circular dependencies
- [ ] All existing tests pass
- [ ] Format matches spec: {emoji} {TYPE}:{MODEL}('{DESC}') {STATUS}

