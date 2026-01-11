# Stravinsky - MCP Bridge (Claude Code Bridge)

**Claude Code MCP server** for multi-model orchestration with OAuth authentication.

## Commands

### Authentication

Stravinsky supports **two authentication methods** for Gemini (OAuth-first with automatic API fallback):

#### Option 1: OAuth (Recommended - Primary Method)

**Full OAuth flow** with automatic token refresh:

```bash
# Login
stravinsky-auth login gemini
stravinsky-auth login openai

# Status
stravinsky-auth status

# Logout
stravinsky-auth logout gemini
```

**When to use:** Primary method for all use cases. Provides automatic fallback to API key on rate limits.

**Auth Priority:**
1. OAuth is tried FIRST (if configured)
2. On OAuth 429 rate limit → Switch to API key for 5 minutes
3. After 5-minute cooldown → Automatically retry OAuth

#### Option 2: API Key (Fallback - Development/Testing)

**Simplest setup** - add `GEMINI_API_KEY` to your `.env` file:

```bash
# Add to .env file in project root
GEMINI_API_KEY=your_api_key_here

# Or use GOOGLE_API_KEY (same effect)
GOOGLE_API_KEY=your_api_key_here
```

**Get your API key:** Visit [Google AI Studio](https://aistudio.google.com/app/apikey)

**When to use:** Development, testing, or as automatic fallback when OAuth hits rate limits.

## Setup in Claude Code

### Installation

**CRITICAL: ALWAYS install with --scope user, @latest, and Python 3.13**

```bash
# CORRECT: User-scoped installation with Python 3.13 and auto-updates
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest

# WRONG: Never use local installation
# ❌ claude mcp add stravinsky -- uvx stravinsky  (NO @latest = stale cache)
# ❌ uv tool install --editable .  (local dev only)
# ❌ claude mcp add --scope user stravinsky -- uvx stravinsky@latest  (missing --python)
```

**Why @latest is REQUIRED:**
- Forces uvx to check PyPI on every Claude restart
- Without it, uvx caches the package and NEVER updates
- You'll be stuck on old versions forever

**Why --python python3.13 is REQUIRED:**
- Stravinsky depends on chromadb, which uses onnxruntime
- onnxruntime does not have wheels for Python 3.14+
- Python 3.13 is the latest stable version with full compatibility
- Forcing Python 3.13 prevents installation/runtime errors on unsupported versions

**Development (local source only):**

```bash
# ONLY for active development on stravinsky itself
uv tool install --editable /path/to/stravinsky
claude mcp add --scope user stravinsky -- stravinsky
```

### Slash Commands (Skills)

Skills are discovered from:
- Project-local: `.claude/commands/**/*.md` (recursive)
- User-global: `~/.claude/commands/**/*.md` (recursive)

Common commands:
- `/strav`: Task Orchestrator & Planner
- `/delphi`: Architecture & Debug Advisor
- `/dewey`: Documentation & Research
- `/get-context`: Refresh Git/Rules/Todo context (renamed from /context to avoid Claude conflict)
- `/health`: Comprehensive system check

## OAuth Flows

### Gemini (Google Antigravity)

- Browser-based OAuth 2.0 with PKCE
- Uses same credentials as Stravinsky
- Supports automatic token refresh

### OpenAI (ChatGPT Plus/Pro)

- Browser-based OAuth on port 1455 (same as Codex CLI)
- Requires ChatGPT Plus/Pro subscription
- Supports automatic token refresh

## Tools (33)

| Category         | Tools                                                                              |
| ---------------- | ---------------------------------------------------------------------------------- |
| **Model Invoke** | `invoke_gemini`, `invoke_openai`, `get_system_health`                              |
| **Environment**  | `get_project_context`, `task_spawn`, `task_status`, `task_list`                    |
| **Agents**       | `agent_spawn`, `agent_output`, `agent_cancel`, `agent_list`, `agent_progress`      |
| **Code Search**  | `ast_grep_search`, `ast_grep_replace`, `grep_search`, `glob_files`                 |
| **LSP**          | `lsp_diagnostics`, `lsp_hover`, `lsp_goto_definition`, `lsp_find_references`, etc. |
| **Sessions**     | `session_list`, `session_read`, `session_search`                                   |
| **Skills**       | `skill_list`, `skill_get`                                                          |

### Agent Tools

Spawn background agents with **full tool access** via Claude Code CLI:

- `agent_spawn(prompt, agent_type, description)` - Launch background agent
- `agent_output(task_id, block)` - Get output (block=true to wait)
- `agent_progress(task_id, lines)` - Real-time progress monitoring
- `agent_cancel(task_id)` - Cancel running agent
- `agent_list()` - List all agent tasks

### LSP Tools (12)

Full Language Server Protocol support for Python (via jedi):

- `lsp_hover` - Type info and docs at position
- `lsp_goto_definition` - Jump to symbol definition
- `lsp_find_references` - Find all usages
- `lsp_document_symbols` - File outline
- `lsp_workspace_symbols` - Search symbols by name
- `lsp_prepare_rename` - Validate rename
- `lsp_rename` - Rename symbol across workspace
- `lsp_code_actions` - Quick fixes and refactorings
- `lsp_code_action_resolve` - Apply specific code action/fix (e.g., fix F401 unused import)
- `lsp_extract_refactor` - Extract code to function or variable (Python via jedi)
- `lsp_servers` - List available LSP servers
- `lsp_diagnostics` - Errors and warnings

### AST-Grep Tools

- `ast_grep_search` - AST-aware code pattern search
- `ast_grep_replace` - AST-aware code replacement

### Semantic Search Tools

- `semantic_search` - Natural language code search with embeddings
- `semantic_index` - Index codebase for semantic search
- `semantic_stats` - View index statistics

**NEW: Automatic File Watching**
```python
# Start background file watcher for automatic reindexing
from mcp_bridge.tools.semantic_search import start_file_watcher

watcher = start_file_watcher(".", provider="ollama", debounce_seconds=2.0)
# File changes now automatically trigger reindexing

# Stop when done
from mcp_bridge.tools.semantic_search import stop_file_watcher
stop_file_watcher(".")
```

**Features:**
- Monitors .py files for create/modify/delete/move events
- Debounces rapid changes (2s default) to batch reindexing
- Thread-safe daemon threads for clean shutdown
- Skips venv, __pycache__, .git, node_modules
- Works with all providers (ollama, gemini, openai, huggingface)

## Agent Prompts (7)

| Prompt            | Purpose                                                       |
| ----------------- | ------------------------------------------------------------- |
| `stravinsky`      | Task orchestration, planning, and goal-oriented execution.    |
| `delphi`          | Strategic technical advisor (GPT-based) for hard debugging.   |
| `dewey`           | Documentation and multi-repository research specialist.       |
| `explore`         | Specialized for codebase-wide search and structural analysis. |
| `frontend`        | UI/UX Engineer (Gemini-optimized) for component prototyping.  |
| `document_writer` | Technical documentation and specification writer.             |
| `multimodal`      | Visual analysis expert for UI screenshots and diagrams.       |

## Project Structure

```
stravinsky/
├── mcp_bridge/           # Python MCP server
│   ├── server.py         # Entry point
│   ├── auth/             # OAuth (Google & OpenAI)
│   ├── tools/            # Model invoke, search, skills
│   ├── prompts/          # Agent system prompts (Stravinsky, Delphi, Dewey, etc.)
│   └── config/           # Bridge configuration
├── .mcp.json             # Claude Code config
├── pyproject.toml        # Build system
└── CLAUDE.md             # This guide
```

## Architecture

1. **MCP Transport**: Uses standard input/output for interaction with Claude Code.
2. **Dynamic Tokens**: OAuth tokens are stored in the system keyring and refreshed on demand.
3. **Specialized Models**:
   - `invoke_gemini`: Best for UI, images, and creative generation.
   - `invoke_openai`: Best for complex reasoning and strategic advice.
4. **Tool Integrity**: All tools match the behavior of the original TypeScript implementation but are ported to native Python for speed and reliability.

## Troubleshooting

### OpenAI "Port 1455 in use"

The Codex CLI uses the same port. Stop it with: `killall codex`

### OpenAI Authentication Failed

- Ensure you have a ChatGPT Plus/Pro subscription.
- Tokens expire occasionally; run `python -m mcp_bridge.auth.cli login openai` to refresh manually if automatic refresh fails.

### Python Version / onnxruntime Errors

If you see errors like `ModuleNotFoundError: No module named 'onnxruntime'` or wheel build failures:

**Root cause**: You're running Python 3.14+ (onnxruntime lacks wheels for these versions)

**Solution**: Reinstall with Python 3.13:
```bash
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest
```

**Why this works**: chromadb → onnxruntime only has pre-built wheels for Python ≤3.13

## Stravinsky MCP (Parallel Agents)

Use Stravinsky MCP tools. **DEFAULT: spawn parallel agents for multi-step tasks.**

### Agent Tools

- `agent_spawn(prompt, agent_type, description)` - Spawn background agent with full tool access
- `agent_output(task_id, block)` - Get results (block=True to wait)
- `agent_progress(task_id)` - Check real-time progress
- `agent_list()` - Overview of all running agents
- `agent_cancel(task_id)` - Stop a running agent

### Agent Types

- `explore` - Codebase search, "where is X?" questions
- `dewey` - Documentation research, implementation examples
- `frontend` - UI/UX work, component design
- `delphi` - Strategic advice, architecture review

### Parallel Execution (MANDATORY)

For ANY task with 2+ independent steps:

1.  **Immediately use agent_spawn** for each independent component
2.  Fire all agents simultaneously, don't wait
3.  Monitor with agent_progress, collect with agent_output

### ULTRATHINK / IRONSTAR

- **ULTRATHINK**: Engage exhaustive deep reasoning, multi-dimensional analysis
- **IRONSTAR**: Maximum parallel execution - spawn agents aggressively for every subtask

---

## Learn More

- [PyPI Package](https://pypi.org/project/stravinsky/)
- [Documentation](https://github.com/GratefulDave/stravinsky)
