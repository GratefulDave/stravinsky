# Stravinsky

**The Avant-Garde MCP Bridge for Claude Code**

*Movement • Rhythm • Precision*

---

## What is Stravinsky?

**Multi-model AI orchestration** with OAuth authentication for Claude Code.

## Features

- 🔐 **OAuth Authentication** - Secure browser-based auth for Google (Gemini) and OpenAI (ChatGPT)
- 🤖 **Multi-Model Support** - Seamlessly invoke Gemini and GPT models from Claude
- 🎯 **Native Subagent Orchestration** - Auto-delegating orchestrator with parallel execution (zero CLI overhead)
- 🛠️ **40 MCP Tools** - Model invocation, code search, semantic search, LSP refactoring, session management, and more
- 🧠 **9 Specialized Native Agents** - Stravinsky (orchestrator), Research Lead, Implementation Lead, Delphi (GPT-5.2 advisor), Dewey (documentation), Explore (code search), Frontend (Gemini 3 Pro High UI/UX), Code Reviewer, Debugger
- 🔄 **Hook-Based Delegation** - PreToolUse hooks enforce delegation patterns with hard boundaries (exit code 2)
- 📝 **LSP Integration** - Full Language Server Protocol support with persistent servers (35x speedup), code refactoring, and advanced navigation
- 🔍 **AST-Aware Search** - Structural code search and refactoring with ast-grep
- 🧠 **Semantic Code Search** - Natural language queries with local embeddings (ChromaDB + Ollama)
- ⚡ **Cost-Optimized Routing** - Free/cheap agents (explore, dewey) always async, expensive (delphi) only when needed

## Quick Start

### Installation

**CRITICAL: Always use --scope user with @latest for auto-updates and Python 3.13**

```bash
# CORRECT: User-level installation with Python 3.13 and automatic updates
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest

# Why this matters:
# - --scope user: Works across all projects (stored in ~/.claude.json)
# - @latest: Auto-checks PyPI on every Claude restart (no stale cache)
# - --python python3.13: Required due to chromadb → onnxruntime dependency (no Python 3.14+ support)
```

**⚠️ Python 3.13 Required**: Stravinsky requires Python 3.13 or earlier. Python 3.14+ is not supported because chromadb depends on onnxruntime, which lacks wheels for Python 3.14+.

**WRONG - Do NOT use these:**

```bash
# ❌ Missing --python python3.13 (will fail on system Python 3.14+)
claude mcp add --global stravinsky -- uvx stravinsky@latest

# ❌ Local scope (only works in one project)
claude mcp add stravinsky -- uvx --python python3.13 stravinsky@latest

# ❌ No @latest (cache never updates, stays on old version)
claude mcp add --global stravinsky -- uvx --python python3.13 stravinsky

# ❌ uv tool install (requires manual upgrades)
uv tool install stravinsky
```

**Development (local editable install):**

```bash
# ONLY for active development on stravinsky source code
cd /path/to/stravinsky
uv tool install --editable . --force
claude mcp add --scope user stravinsky -- stravinsky
```

### Authentication

Stravinsky supports **two authentication methods** for Gemini (OAuth-first with automatic API fallback):

#### Option 1: OAuth (Recommended - Primary Method)

**Full OAuth flow** with automatic token refresh:

```bash
# Login to Google (Gemini)
stravinsky-auth login gemini

# Login to OpenAI (ChatGPT Plus/Pro required)
stravinsky-auth login openai

# Check status
stravinsky-auth status

# Logout
stravinsky-auth logout gemini
```

**When to use:** Primary method for all use cases. Provides automatic fallback to API key on rate limits.

**Rate Limit Architecture:**
- **OAuth**: Lower rate limits, but convenient (no API key management)
- **API Key**: **Tier 3 high quotas** - automatic fallback for heavy usage

**Auth Priority:**
1. OAuth is tried FUWT (if configured)
2. On OAuth 429 rate limit → **Automatically switch to API key** (Tier 3 quotas) for 5 minutes
3. After 5-minute cooldown → Retry OAuth

#### Option 2: API Key (**Tier 3 High Quotas** - Automatic Fallback)

**CRITICAL**: Use a **Tier 3 API key** for high-volume usage. OAuth has lower limits and automatically falls back to your API key.

**Setup** - add your Gemini API key to `.env`:

```bash
# Add to your .env file (or export in shell)
GEMINI_API_KEY=your_tier_3_api_key_here

# Or use GOOGLE_API_KEY (same effect)
GOOGLE_API_KEY=your_tier_3_api_key_here
```

**Get your API key:**
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create an API key (ensure it's Tier 3 for high quotas)
3. Add to `.env` file in your project root

**When to use:**
- **Primary**: Automatic fallback when OAuth rate limits are exhausted (recommended for all users)
- Development/testing without OAuth setup

**Secure Token Storage:**

OAuth tokens are stored securely with automatic fallback:
- **Primary**: System keyring (macOS Keychain, Linux Secret Service, Windows Credential Locker)
- **Fallback**: Encrypted files at `~/.stravinsky/tokens/` using Fernet symmetric encryption
- **Encryption**: AES-128-CBC with keys stored at `~/.stravinsky/tokens/.key` (0o600 permissions)
- **No password prompts**: Seamless authentication across all terminal sessions after initial login
- **Global access**: Works everywhere after one-time authentication per provider

#### Troubleshooting: Password Prompts (macOS)

If you experience persistent password prompts when authenticating, configure keyring to bypass macOS Keychain:

```bash
# 1. Create keyring config directory
mkdir -p ~/.config/python_keyring

# 2. Configure keyring to use fail backend (bypasses Keychain entirely)
cat <<EOT > ~/.config/python_keyring/keyringrc.cfg
[backend]
default-keyring = keyring.backends.fail.Keyring
EOT

# 3. Verify configuration
cat ~/.config/python_keyring/keyringrc.cfg

# 4. Re-authenticate (tokens will be stored in encrypted files only)
stravinsky-auth login gemini
```

This configuration stores tokens in encrypted files at `~/.stravinsky/tokens/` instead of macOS Keychain, eliminating password prompts across terminal sessions. See [docs/reports/KEYRING_AUTH_FIX.md](docs/reports/KEYRING_AUTH_FIX.md) for detailed information.

### Slash Commands

Slash commands are discovered from:
- Project-local: `.claude/commands/**/*.md` (recursive)
- User-global: `~/.claude/commands/**/*.md` (recursive)

Commands can be organized in subdirectories (e.g., `.claude/commands/strav/stravinsky.md`).

## Native Subagent Architecture (PRIMARY)

Stravinsky is architected around the **Native Subagent Pattern**. This design delegates specialized tasks to standalone Claude Code agents, enabling massive parallelism and reducing orchestrator cognitive load.

### Why Native Subagents?
- **True Parallelism**: Spawn multiple agents (Explore, Dewey, Reviewer) simultaneously using the `Task` tool.
- **Zero Bridge Latency**: Agents interact directly with the project codebase using native tools.
- **Specialized Context**: Each agent type has a bespoke system prompt and focused toolset.

---

## Model Proxy (NEW in v0.4.58)

To solve the "Head-of-Line Blocking" problem in MCP stdio, Stravinsky now includes a dedicated **Model Proxy**.

### The Problem:
When Claude calls `invoke_gemini` directly through MCP, the entire stdio communication channel is blocked until the model finishes generating. This prevents parallel execution and makes the UI feel sluggish.

### The Solution:
The **Stravinsky Model Proxy** runs as a separate FastAPI process. Model requests are offloaded to this process, allowing the MCP bridge to handle other tool calls immediately.

### Performance Benefits:
- **Async Concurrency**: Handle 20+ simultaneous model calls with <10ms overhead.
- **Zero CLI Blocking**: Keep the main Claude CLI responsive during long generations.
- **Observability**: Real-time request tracking, Process-Time headers, and trace IDs.

### Usage:
1. **Start the Proxy** in a separate terminal:
   ```bash
   stravinsky-proxy
   ```
2. **Enable in Claude**: Set the environment variable:
   ```bash
   export STRAVINSKY_USE_PROXY=true
   ```

---

## Features

| Category         | Tools                                                                              |
| ---------------- | ---------------------------------------------------------------------------------- |
| **Model Invoke** | `invoke_gemini`, `invoke_gemini_agentic`, `invoke_openai` (3 tools)                |
| **Environment**  | `get_project_context`, `get_system_health`, `stravinsky_version`, `system_restart`, `semantic_health`, `lsp_health` (6 tools) |
| **Background Tasks** | `task_spawn`, `task_status`, `task_list` (3 tools)                             |
| **Agents**       | `agent_spawn`, `agent_output`, `agent_cancel`, `agent_list`, `agent_progress`, `agent_retry` (6 tools) |
| **Code Search**  | `ast_grep_search`, `ast_grep_replace`, `grep_search`, `glob_files` (4 tools)       |
| **Semantic**     | `semantic_search`, `hybrid_search`, `semantic_index`, `semantic_stats`, `start_file_watcher`, `stop_file_watcher`, `cancel_indexing`, `delete_index`, `list_file_watchers`, `multi_query_search`, `decomposed_search`, `enhanced_search` (12 tools) |
| **LSP**          | `lsp_diagnostics`, `lsp_hover`, `lsp_goto_definition`, `lsp_find_references`, `lsp_document_symbols`, `lsp_workspace_symbols`, `lsp_prepare_rename`, `lsp_rename`, `lsp_code_actions`, `lsp_code_action_resolve`, `lsp_extract_refactor`, `lsp_servers` (12 tools) |
| **Sessions**     | `session_list`, `session_read`, `session_search` (3 tools)                         |
| **Skills**       | `skill_list`, `skill_get` (2 tools)                                                |

### LSP Performance & Refactoring

The Phase 2 update introduced the `LSPManager`, which maintains persistent language server instances:

- **35x Speedup**: Subsequent LSP calls are near-instant because the server no longer needs to re-initialize and re-index the codebase for every request
- **Code Refactoring**: New support for `lsp_extract_refactor` allows automated code extraction (e.g., extracting a method or variable) with full symbol resolution
- **Code Actions**: `lsp_code_action_resolve` enables complex, multi-step refactoring workflows with automatic fixes for diagnostics

### Semantic Code Search

Natural language code search powered by embeddings. Find code by meaning, not just keywords.

**Prerequisites:**

```bash
# Install Ollama (default provider - free, local)
brew install ollama

# Pull the recommended lightweight embedding model (274MB)
ollama pull nomic-embed-text

# Or for better accuracy (670MB, slower):
ollama pull mxbai-embed-large
```

**Recommended model:** `nomic-embed-text` is lightweight (274MB), fast, and works great for code search. It's the best choice for most users, especially on space-constrained systems like MacBooks.

**Workflow:**

```bash
# STEP 1: Initial indexing (REQUIRED - run once per project)
semantic_index(project_path=".", provider="ollama")

# STEP 2: Enable auto-updates (OPTIONAL - recommended for active projects)
start_file_watcher(".", provider="ollama", debounce_seconds=2.0)

# STEP 3: Search your codebase with natural language
semantic_search(query="OAuth authentication logic", n_results=5)
semantic_stats()  # View index statistics

# STEP 4: Stop watching when done (optional - watcher cleans up on exit)
stop_file_watcher(".")

# OPTIONAL: Cancel ongoing indexing (for large codebases)
cancel_indexing(project_path=".", provider="ollama")

# OPTIONAL: Delete indexes
delete_index(project_path=".", provider="ollama")  # Delete ollama index for this project
delete_index(project_path=".")  # Delete all provider indexes for this project
delete_index(delete_all=True)  # Delete ALL indexes for ALL projects
```

**⚠️ Important:** You MUST run `semantic_index()` first before using semantic search or starting the FileWatcher. If you skip this step:
- `semantic_search()` will return no results
- `start_file_watcher()` will show a warning but still work (indexes on first file change)

**Example queries:**
- "find authentication logic"
- "error handling in API endpoints"
- "database connection pooling"

**Providers:**

| Provider | Model | Size | Cost | Setup |
|----------|-------|------|------|-------|
| `ollama` (default) | nomic-embed-text (recommended) | 274MB | Free/local | `ollama pull nomic-embed-text` |
| `ollama` | mxbai-embed-large (advanced) | 670MB | Free/local | `ollama pull mxbai-embed-large` |
| `gemini` | gemini-embedding-001 | N/A | OAuth/cloud | `stravinsky-auth login gemini` |
| `openai` | text-embedding-3-small | N/A | OAuth/cloud | `stravinsky-auth login openai` |

**Technical details:**
- **AST-aware chunking**: Python files split by functions/classes for better semantic boundaries
- **Persistent storage**: ChromaDB at `~/.stravinsky/vectordb/<project>_<provider>/`
- **Async parallel embeddings**: 10 concurrent for fast indexing
- **Automatic file watching**: Background reindexing on code changes with configurable debouncing (2s default)

## Native Subagents (9)

Configured in `.claude/agents/*.md`:

| Agent            | Purpose                                                               | Location |
| ---------------- | --------------------------------------------------------------------- | -------- |
| `stravinsky`     | Task orchestration with 32k extended thinking (Sonnet 4.5)            | .claude/agents/stravinsky.md |
| `research-lead`  | Research coordinator - spawns explore/dewey, synthesizes findings (Gemini Flash) | .claude/agents/research-lead.md |
| `implementation-lead` | Implementation coordinator - spawns frontend/debugger/reviewer (Haiku) | .claude/agents/implementation-lead.md |
| `explore`        | Codebase search and structural analysis (Gemini 3 Flash)              | .claude/agents/explore.md |
| `dewey`          | Documentation research and web search (Gemini 3 Flash)                | .claude/agents/dewey.md |
| `code-reviewer`  | Security, quality, and best practice analysis (Claude Sonnet)         | .claude/agents/code-reviewer.md |
| `debugger`       | Root cause analysis and fix strategies (Claude Sonnet)                | .claude/agents/debugger.md |
| `frontend`       | UI/UX implementation with creative generation (Gemini 3 Pro High)     | .claude/agents/frontend.md |
| `delphi`         | Strategic architecture advisor with 32k thinking (GPT-5.2 Medium)     | .claude/agents/delphi.md |

## Development

```bash
# Install in development mode
uv pip install -e .

# Run server
stravinsky
```

## Project Structure

```
stravinsky/
├── .claude/                      # Claude Code configuration
│   ├── agents/                   # Native subagent configurations (7 agents)
│   │   ├── stravinsky.md         # Orchestrator (auto-delegated)
│   │   ├── explore.md            # Code search specialist
│   │   ├── dewey.md              # Documentation research
│   │   ├── code-reviewer.md      # Quality analysis
│   │   ├── debugger.md           # Root cause analysis
│   │   ├── frontend.md           # UI/UX specialist
│   │   ├── delphi.md             # Strategic advisor (GPT-5.2)
│   │   └── HOOKS.md              # Hook architecture guide
│   ├── commands/                 # Slash commands (skills)
│   │   ├── stravinsky.md         # /strav orchestrator
│   │   ├── delphi.md             # /delphi strategic advisor
│   │   ├── dewey.md              # /dewey documentation research
│   │   ├── publish.md            # /publish PyPI release
│   │   ├── review.md             # /review code review
│   │   ├── verify.md             # /verify post-implementation
│   │   └── version.md            # /version diagnostic info
│   ├── hooks/                    # Native Claude Code hooks (11 hooks)
│   │   ├── stravinsky_mode.py    # PreToolUse delegation enforcer
│   │   ├── context.py            # UserPromptSubmit context injection
│   │   ├── todo_continuation.py  # UserPromptSubmit todo continuation
│   │   ├── truncator.py          # PostToolUse output truncation
│   │   ├── tool_messaging.py     # PostToolUse user messaging
│   │   ├── edit_recovery.py      # PostToolUse edit backup
│   │   ├── todo_delegation.py    # PostToolUse parallel reminder
│   │   ├── parallel_execution.py # PostToolUse parallel enforcement
│   │   ├── notification_hook.py  # PreToolUse agent spawn notifications
│   │   ├── subagent_stop.py      # PostToolUse agent completion handling
│   │   └── pre_compact.py        # PreCompact context preservation
│   ├── skills/                   # Skill library (empty, skills in commands/)
│   ├── settings.json             # Hook configuration
│   └── HOOKS_INTEGRATION.md      # Hook integration guide
├── mcp_bridge/                   # Python MCP server
│   ├── server.py                 # MCP server entry point
│   ├── server_tools.py           # Tool definitions
│   ├── auth/                     # OAuth authentication
│   │   ├── oauth.py              # Google OAuth (Gemini)
│   │   ├── openai_oauth.py       # OpenAI OAuth (ChatGPT)
│   │   ├── token_store.py        # Keyring storage
│   │   ├── token_refresh.py      # Auto-refresh tokens
│   │   └── cli.py                # stravinsky-auth CLI
│   ├── tools/                    # MCP tool implementations
│   │   ├── model_invoke.py       # invoke_gemini, invoke_openai
│   │   ├── agent_manager.py      # agent_spawn, agent_output, etc.
│   │   ├── code_search.py        # ast_grep, grep, glob
│   │   ├── semantic_search.py    # semantic_search, semantic_index, semantic_stats
│   │   ├── session_manager.py    # session_list, session_read, etc.
│   │   ├── skill_loader.py       # skill_list, skill_get
│   │   ├── project_context.py    # get_project_context
│   │   ├── lsp/                  # LSP tool implementations
│   │   └── templates.py          # Project templates
│   ├── prompts/                  # Agent system prompts (legacy CLI)
│   │   ├── stravinsky.py         # Legacy orchestrator prompt
│   │   ├── delphi.py             # Legacy advisor prompt
│   │   ├── dewey.py              # Legacy research prompt
│   │   ├── explore.py            # Legacy search prompt
│   │   ├── frontend.py           # Legacy UI/UX prompt
│   │   └── multimodal.py         # Multimodal analysis prompt
│   ├── hooks/                    # MCP internal hooks (17+ hooks)
│   │   ├── manager.py            # Hook orchestration
│   │   ├── truncator.py          # Output truncation
│   │   ├── parallel_enforcer.py  # Parallel execution
│   │   ├── todo_enforcer.py      # Todo continuation
│   │   └── ...                   # 13+ more optimization hooks
│   ├── native_hooks/             # Native Claude Code hooks
│   │   ├── stravinsky_mode.py    # PreToolUse delegation enforcer
│   │   ├── tool_messaging.py     # PostToolUse user messaging
│   │   ├── todo_delegation.py    # TodoWrite parallel reminder
│   │   ├── todo_continuation.py  # UserPromptSubmit todo injection
│   │   ├── context.py            # UserPromptSubmit context
│   │   ├── truncator.py          # PostToolUse truncation
│   │   └── edit_recovery.py      # PostToolUse backup
│   ├── cli/                      # CLI utilities
│   │   └── session_report.py     # Session analysis
│   ├── config/                   # Configuration
│   │   └── hooks.py              # Hook configuration
│   └── utils/                    # Utility functions
├── .stravinsky/                  # Agent execution logs (gitignored)
├── assets/                       # Logo, images
├── docs/                         # Additional documentation
├── logs/                         # Application logs
├── tests/                        # Test suite
├── pyproject.toml                # Build configuration
├── uv.lock                       # Dependency lock
├── ARCHITECTURE.md               # Architecture guide (oh-my-opencode comparison)
├── CLAUDE.md                     # Project instructions
├── INSTALL.md                    # Installation guide
└── README.md                     # This file
```

## Troubleshooting

### OpenAI "Port 1455 in use"

The Codex CLI uses the same port. Stop it with: `killall codex`

### OpenAI Authentication Failed

- Ensure you have a ChatGPT Plus/Pro subscription
- Tokens expire occasionally; run `stravinsky-auth login openai` to refresh

### Claude Code Not Loading Latest Version After Update

**Problem:** After deploying a new version to PyPI, Claude Code still uses the old cached version even after restart.

**Root Cause:** `uvx` caches packages and doesn't automatically check for updates. This is a known uvx behavior that affects all packages, not just Stravinsky.

**Solution - Force Reinstall:**

```bash
# Option 1: Run latest version with uvx (if using uvx in .mcp.json)
uvx stravinsky@latest

# Option 2: Upgrade with uv tool (if installed globally)
uv tool install --upgrade --force stravinsky
# or reinstall all tools:
uv tool upgrade --all --reinstall

# Option 3: Clear uvx cache entirely (nuclear option)
uv cache prune

# Option 4: Remove and re-add MCP server
claude mcp remove stravinsky
claude mcp add stravinsky -- uvx stravinsky@latest

# After any option, restart Claude Code
claude restart
```

**Verify Version:**

```bash
# Check installed version
stravinsky --version
# or
python -c "import mcp_bridge; print(mcp_bridge.__version__)"

# Check PyPI latest version
curl -s https://pypi.org/pypi/stravinsky/json | python -c "import sys, json; print(json.load(sys.stdin)['info']['version'])"
```

## License

MIT

---
