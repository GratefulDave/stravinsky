<div align="center">
  <img src="https://raw.githubusercontent.com/GratefulDave/stravinsky/main/assets/logo.png" width="300" alt="Stravinsky Logo">
  <h1>Stravinsky</h1>
  <p><strong>The Avant-Garde MCP Bridge for Claude Code</strong></p>
  <p><em>Movement • Rhythm • Precision</em></p>
</div>

---

## What is Stravinsky?

**Multi-model AI orchestration** with OAuth authentication for Claude Code.

## Features

- 🔐 **OAuth Authentication** - Secure browser-based auth for Google (Gemini) and OpenAI (ChatGPT)
- 🤖 **Multi-Model Support** - Seamlessly invoke Gemini and GPT models from Claude
- 🎯 **Native Subagent Orchestration** - Auto-delegating orchestrator with parallel execution (zero CLI overhead)
- 🛠️ **38 MCP Tools** - Model invocation, code search, semantic search, LSP refactoring, session management, and more
- 🧠 **9 Specialized Native Agents** - Stravinsky (orchestrator), Research Lead, Implementation Lead, Delphi (GPT-5.2 advisor), Dewey (documentation), Explore (code search), Frontend (Gemini 3 Pro High UI/UX), Code Reviewer, Debugger
- 🔄 **Hook-Based Delegation** - PreToolUse hooks enforce delegation patterns with hard boundaries (exit code 2)
- 📝 **LSP Integration** - Full Language Server Protocol support with persistent servers (35x speedup), code refactoring, and advanced navigation
- 🔍 **AST-Aware Search** - Structural code search and refactoring with ast-grep
- 🧠 **Semantic Code Search** - Natural language queries with local embeddings (ChromaDB + Ollama)
- ⚡ **Cost-Optimized Routing** - Free/cheap agents (explore, dewey) always async, expensive (delphi) only when needed

## Quick Start

### Installation

**From PyPI (Recommended):**

```bash
# One-shot with uvx - no installation needed!
claude mcp add stravinsky -- uvx stravinsky

# Or install globally first:
uv tool install stravinsky
claude mcp add stravinsky -- stravinsky
```

**From Source (for development):**

```bash
uv tool install --editable /path/to/stravinsky
claude mcp add stravinsky -- stravinsky
```

### Authentication

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

### Slash Commands

Slash commands are discovered from:
- Project-local: `.claude/commands/**/*.md` (recursive)
- User-global: `~/.claude/commands/**/*.md` (recursive)

Commands can be organized in subdirectories (e.g., `.claude/commands/strav/stravinsky.md`).

## Native Subagent Architecture

Stravinsky uses **native Claude Code subagents** (.claude/agents/) with automatic delegation:

### How It Works

1. **Auto-Delegation**: Claude Code automatically delegates complex tasks to the Stravinsky orchestrator
2. **Hook-Based Control**: PreToolUse hooks intercept direct tool calls and enforce delegation patterns
3. **Parallel Execution**: Task tool enables true parallel execution of specialist agents
4. **Multi-Model Routing**: Specialists use invoke_gemini/openai MCP tools for multi-model access

### Agent Types

| Agent | Model | Cost | Use For |
|-------|-------|------|---------|
| **stravinsky** | Claude Sonnet 4.5 (32k thinking) | Moderate | Auto-delegating orchestrator (primary) |
| **explore** | Gemini 3 Flash (via MCP) | Free | Code search, always async |
| **dewey** | Gemini 3 Flash + WebSearch | Cheap | Documentation research, always async |
| **code-reviewer** | Claude Sonnet (native) | Cheap | Quality analysis, always async |
| **debugger** | Claude Sonnet (native) | Medium | Root cause (after 2+ failures) |
| **frontend** | Gemini 3 Pro High (via MCP) | Medium | ALL visual changes (blocking) |
| **delphi** | GPT-5.2 Medium (via MCP) | Expensive | Architecture (after 3+ failures) |

### Delegation Rules (oh-my-opencode Pattern)

- **Always Async**: explore, dewey, code-reviewer (free/cheap)
- **Blocking**: debugger (2+ failures), frontend (ALL visual), delphi (3+ failures or architecture)
- **Never Work Alone**: Orchestrator blocks Read/Grep/Bash via PreToolUse hooks

### ULTRATHINK / ULTRAWORK

- **ULTRATHINK**: Engage exhaustive deep reasoning with extended thinking budget (32k tokens)
- **ULTRAWORK**: Maximum parallel execution - spawn all async agents immediately
````

## Tools (38)

| Category         | Tools                                                                              |
| ---------------- | ---------------------------------------------------------------------------------- |
| **Model Invoke** | `invoke_gemini`, `invoke_openai`, `get_system_health`                              |
| **Environment**  | `get_project_context`, `task_spawn`, `task_status`, `task_list`                    |
| **Agents**       | `agent_spawn`, `agent_output`, `agent_cancel`, `agent_list`, `agent_progress`, `agent_retry` |
| **Code Search**  | `ast_grep_search`, `ast_grep_replace`, `grep_search`, `glob_files`                 |
| **Semantic**     | `semantic_search`, `semantic_index`, `semantic_stats`                              |
| **LSP**          | `lsp_diagnostics`, `lsp_hover`, `lsp_goto_definition`, `lsp_find_references`, `lsp_document_symbols`, `lsp_workspace_symbols`, `lsp_prepare_rename`, `lsp_rename`, `lsp_code_actions`, `lsp_code_action_resolve`, `lsp_extract_refactor`, `lsp_servers` (12 tools) |
| **Sessions**     | `session_list`, `session_read`, `session_search`                                   |
| **Skills**       | `skill_list`, `skill_get`                                                          |

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

# Pull the embedding model
ollama pull nomic-embed-text
```

**Usage:**

```python
# Via MCP tools in Claude Code
semantic_index(project_path=".", provider="ollama")  # First-time indexing
semantic_search(query="OAuth authentication logic", n_results=5)
semantic_stats()  # View index statistics
```

**Example queries:**
- "find authentication logic"
- "error handling in API endpoints"
- "database connection pooling"

**Providers:**

| Provider | Model | Cost | Setup |
|----------|-------|------|-------|
| `ollama` (default) | nomic-embed-text | Free/local | `ollama pull nomic-embed-text` |
| `gemini` | gemini-embedding-001 | OAuth/cloud | `stravinsky-auth login gemini` |
| `openai` | text-embedding-3-small | OAuth/cloud | `stravinsky-auth login openai` |

**Technical details:**
- **AST-aware chunking**: Python files split by functions/classes for better semantic boundaries
- **Persistent storage**: ChromaDB at `~/.stravinsky/vectordb/<project>_<provider>/`
- **Async parallel embeddings**: 10 concurrent for fast indexing

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
│   │   ├── stravinsky.md         # /stravinsky orchestrator
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

## License

MIT

---
