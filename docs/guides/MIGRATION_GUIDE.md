# Stravinsky Migration Guide (v0.4.x to v0.5.x)

This guide helps you transition from legacy slash commands and `agent_spawn` patterns to the modern **Native Subagent Architecture**.

---

## Prerequisites

Before migrating, ensure your installation uses the correct Python version:

```bash
# Recommended installation (Python 3.11-3.13 required)
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest

# Development installation
uv pip install -e .
```

**Python Version Requirement:** Stravinsky requires Python 3.11-3.13. Python 3.14+ is not supported due to chromadb/onnxruntime dependencies.

---

## 1. Stop Using Slash Commands

Legacy slash commands (like `/stravinsky`, `/delphi`, `/review`) are now **DEPRECATED**.

### Old Pattern (Manual):
```bash
/stravinsky "Refactor the authentication logic"
```

### New Pattern (Automatic):
Just type your request normally in the main Claude CLI:
```
Refactor the authentication logic
```
Claude Code will automatically detect the complexity and delegate to the **Stravinsky Orchestrator** native subagent.

---

## 2. Transition from `agent_spawn` to `Task`

The `agent_spawn` MCP tool is now considered **legacy**. New subagents should use the native Claude Code `Task` tool for delegation.

### Old Pattern (`agent_spawn`):
```python
agent_spawn(
    agent_type="explore",
    prompt="Find all API endpoints",
    description="Search API"
)
```

### New Pattern (`Task`):
```python
Task(
    subagent_type="explore",
    prompt="Find all API endpoints"
)
```

**Benefits of `Task`:**
- **Zero Overhead**: No CLI subprocess spawning.
- **Direct Results**: Results are returned directly to the caller (no `agent_output` needed).
- **Parallel by Default**: Claude Code handles parallel task execution natively.

---

## 3. Enable the Model Proxy (CRITICAL)

To prevent the Claude CLI from blocking during long model generations, you MUST enable the Model Proxy.

1. **Start the Proxy**:
   ```bash
   stravinsky-proxy
   ```

2. **Configure Claude**:
   Add this to your `.zshrc`, `.bashrc`, or `.env`:
   ```bash
   export STRAVINSKY_USE_PROXY=true
   ```

---

## 4. Update Custom Hooks

If you have custom hooks in `.claude/hooks/`, migrate them to the **Unified Hook Interface**.

### Old Hook (Standalone):
```python
# My custom hook reading from stdin...
```

### New Hook (Unified):
```python
from mcp_bridge.hooks.events import HookPolicy, EventType

class MyPolicy(HookPolicy):
    @property
    def event_type(self) -> EventType:
        return EventType.POST_TOOL_CALL
        
    async def evaluate(self, event: ToolCallEvent):
        # Your logic here
        pass
```

Register your new policy in `mcp_bridge/hooks/__init__.py` or run it as a native script with `policy.run_as_native()`.

---

## 5. Configure API Key Fallback (Recommended)

For high-volume usage, add an API key fallback to avoid OAuth rate limits:

```bash
# Add to your .env file
GEMINI_API_KEY=your_api_key_here
```

**How it works:**
1. OAuth is tried first (if configured)
2. On OAuth 429 rate limit - automatically switch to API key for 5 minutes
3. After 5-minute cooldown - retry OAuth

---

## Available Commands Reference

| Command | Description |
|---------|-------------|
| `stravinsky` | Start the MCP server |
| `stravinsky --version` | Check installed version |
| `stravinsky-auth` | Authentication CLI |
| `stravinsky-proxy` | Start proxy mode |

**Authentication commands:**
```bash
stravinsky-auth login gemini    # Authenticate with Google
stravinsky-auth login openai    # Authenticate with OpenAI
stravinsky-auth status          # Check authentication status
stravinsky-auth logout gemini   # Remove Gemini tokens
stravinsky-auth logout openai   # Remove OpenAI tokens
```

---

## Need Help?

If you encounter issues during migration, please check the [Troubleshooting Guide](./TROUBLESHOOTING.md) or open an issue on GitHub.
