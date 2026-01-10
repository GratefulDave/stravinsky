# Stravinsky Usage Guide

Complete reference for all Stravinsky MCP tools and features.

---

## Model Invocation

### invoke_gemini

Invoke Google's Gemini models with OAuth authentication.

```
invoke_gemini(prompt, model, temperature, max_tokens, thinking_budget)
```

**Authentication:**
- Uses Google OAuth 2.0 with PKCE (Proof Key for Code Exchange)
- Connects to Google Antigravity API
- Requires Google account with Gemini access
- Setup: `stravinsky-auth login gemini`
- Tokens stored securely in system keyring (auto-refresh enabled)

**Parameters:**
- `prompt` (required): The prompt to send
- `model`: Model to use (default: `gemini-3-flash`)
  - `gemini-3-flash` - Fast, efficient (maps to Antigravity's flash model)
  - `gemini-3-pro` - More capable (maps to Antigravity's pro model)
  - Custom model IDs supported
- `temperature`: 0.0-2.0 (default: 0.7)
- `max_tokens`: Max response tokens (default: 8192)
- `thinking_budget`: Tokens reserved for internal reasoning (default: 0)
- `agent_context` (optional): Agent metadata for logging
  - `agent_type`: Type of agent (explore, delphi, frontend, etc.)
  - `task_id`: Background task ID
  - `description`: What the agent is doing
- `image_path` (optional): Path to image file for multimodal analysis
  - Supported formats: PNG, JPG, JPEG, GIF, WEBP, PDF
  - Enables vision capabilities for screenshot/diagram analysis

**Model Routing:**
Stravinsky automatically maps friendly model names to Antigravity API model IDs:
- `gemini-3-flash` → Uses Antigravity's flash model
- `gemini-3-pro` → Uses Antigravity's pro model
- Direct model IDs are passed through unchanged

**Example:**
```
Use invoke_gemini with prompt "Explain quantum computing" and thinking_budget 1000
```

**Use Cases:**
- UI/UX generation and component design
- Creative content and documentation writing
- Multimodal analysis (images, diagrams) - use `image_path` parameter
- Fast prototyping and code generation

**Agent Context Logging:**

When `agent_context` is provided, invocations are logged with agent metadata:
```
[explore] → gemini-3-flash: Find all database models...
[delphi] → gemini-3-flash: Review this architecture...
[direct] → gemini-3-flash: Explain quantum computing...
```

This helps track which agent made which request and monitor model usage by agent type.

**Example with context:**
```
invoke_gemini(
    prompt="Find all API endpoints",
    agent_context={"agent_type": "explore", "description": "API search"}
)
# Logs: [explore] → gemini-3-flash: Find all API endpoints
```

**Multimodal Vision Example:**
```
invoke_gemini(
    prompt="Analyze this screenshot for accessibility issues",
    image_path="/path/to/screenshot.png",
    agent_context={"agent_type": "multimodal"}
)
# Enables vision analysis of the screenshot
```

### invoke_openai

Invoke OpenAI GPT models via ChatGPT backend with OAuth authentication.

```
invoke_openai(prompt, model, temperature, max_tokens, thinking_budget)
```

**Authentication:**
- Uses ChatGPT OAuth 2.0 with PKCE (identical to Codex CLI flow)
- **Requires ChatGPT Plus or Pro subscription**
- Connects to `https://chatgpt.com/backend-api/codex/responses`
- Setup: `stravinsky-auth login openai`
- Browser authentication on port 1455 (same as Codex CLI)
- Tokens stored securely in system keyring (auto-refresh enabled)

**OAuth Implementation:**
Replicates the `opencode-openai-codex-auth` plugin:
- Client ID: `app_EMoamEEZ73f0CkXaXp7hrann`
- PKCE with S256 (SHA-256) code challenge
- Fetches official Codex instructions from GitHub (`openai/codex` repository)
- SSE (Server-Sent Events) streaming for real-time responses
- Extracts account ID from JWT token for proper attribution

**Parameters:**
- `prompt` (required): The prompt to send
- `model`: Model to use (default: `gpt-5.2-codex`)
  - `gpt-5.2-codex` - Latest Codex model (recommended)
  - `gpt-5.1-codex` - Previous generation
  - `gpt-5.1-codex-max` - Extended context variant
- `temperature`: 0.0-2.0 (default: 0.7)
- `max_tokens`: Max response tokens (default: 4096)
- `thinking_budget`: Tokens reserved for reasoning (default: 0)
  - When > 0, sets reasoning effort to "high"
  - Enables extended thinking capabilities
- `agent_context` (optional): Agent metadata for logging
  - `agent_type`: Type of agent (explore, delphi, frontend, etc.)
  - `task_id`: Background task ID
  - `description`: What the agent is doing

**Port 1455 Requirement:**
OpenAI OAuth requires port 1455 for the callback handler. If you get a port conflict:
```bash
# Stop Codex CLI if running
killall codex

# Or use Codex CLI directly
codex login
```

**Example:**
```
Use invoke_openai with prompt "Design a REST API with authentication" and model "gpt-5.2-codex"
```

**Use Cases:**
- Complex reasoning and strategic advice
- Architecture reviews and design decisions
- Code review and security analysis
- Advanced debugging and problem-solving

**Agent Context Logging:**

When `agent_context` is provided, invocations are logged with agent metadata:
```
[delphi] → gpt-5.2-codex: Review authentication architecture...
[explore] → gpt-5.2-codex: Analyze security vulnerabilities...
```

**Example with extended thinking:**
```
invoke_openai(
    prompt="Design a scalable microservices architecture",
    model="gpt-5.2-codex",
    thinking_budget=2000,
    agent_context={"agent_type": "delphi", "description": "Architecture design"}
)
# Logs: [delphi] → gpt-5.2-codex: Design a scalable...
# Uses extended reasoning for complex architecture decisions
```

---

## Agent System

### agent_spawn

Spawn a background agent with full Claude Code tool access.

```
agent_spawn(prompt, agent_type, description)
```

**Parameters:**
- `prompt` (required): Task for the agent
- `agent_type`: Type of agent (see below)
- `description`: Short description for tracking

**Agent Types:**
| Type | Purpose |
|------|---------|
| `explore` | Codebase search, structural analysis |
| `dewey` | Documentation research, examples |
| `frontend` | UI/UX work, component design |
| `delphi` | Strategic advice, architecture review |
| `stravinsky` | Task orchestration, planning |
| `planner` | Pre-implementation planning (Opus) |
| `document_writer` | Technical documentation |
| `multimodal` | Visual analysis, screenshots |

**Example:**
```
Use agent_spawn with prompt "Find all API endpoints" and agent_type "explore"
```

### agent_output

Get output from a spawned agent.

```
agent_output(task_id, block)
```

**Parameters:**
- `task_id` (required): ID from agent_spawn
- `block`: Wait for completion (default: true)

### agent_progress

Check real-time progress of an agent.

```
agent_progress(task_id, lines)
```

**Parameters:**
- `task_id` (required): ID from agent_spawn
- `lines`: Number of recent lines to show

### agent_list

List all running and completed agents.

```
agent_list()
```

### agent_cancel

Cancel a running agent.

```
agent_cancel(task_id)
```

---

## Code Search

### ast_grep_search

AST-aware code pattern search using ast-grep.

```
ast_grep_search(pattern, path, language)
```

**Example:**
```
Use ast_grep_search with pattern "async function $NAME($_)" and language "typescript"
```

### ast_grep_replace

AST-aware code replacement.

```
ast_grep_replace(pattern, replacement, path, language)
```

### grep_search

Traditional regex-based search.

```
grep_search(pattern, path, file_pattern)
```

### glob_files

Find files by pattern.

```
glob_files(pattern, path)
```

---

## Health & Diagnostics

### semantic_health

Check the health of the semantic search system, including embedding providers and vector database.

```
semantic_health()
```

---

## File Watcher Tools

Tools for real-time file monitoring and automatic re-indexing.

### start_file_watcher

Start watching a project directory for file changes.

```
start_file_watcher(project_path, provider, debounce_seconds)
```

**Parameters:**
- `project_path`: Path to the project root
- `provider`: Embedding provider (default: "ollama")
- `debounce_seconds`: Time to wait before reindexing (default: 2.0)

### stop_file_watcher

Stop watching a project directory.

```
stop_file_watcher(project_path)
```

### list_file_watchers

List all active file watchers.

```
list_file_watchers()
```

---

## LSP Tools

```
lsp_health()
```

### get_system_health

Comprehensive health check for the entire Stravinsky system.

```
get_system_health()
```

---

## LSP Tools

Full Language Server Protocol support for Python.

### lsp_diagnostics

Get errors and warnings for a file.

```
lsp_diagnostics(file_path)
```

### lsp_hover

Get type information at a position.

```
lsp_hover(file_path, line, character)
```

### lsp_goto_definition

Jump to symbol definition.

```
lsp_goto_definition(file_path, line, character)
```

### lsp_find_references

Find all usages of a symbol.

```
lsp_find_references(file_path, line, character)
```

### lsp_document_symbols

Get file outline/structure.

```
lsp_document_symbols(file_path)
```

### lsp_workspace_symbols

Search symbols across workspace.

```
lsp_workspace_symbols(query)
```

### lsp_health

Check the health and status of the persistent LSP servers.

```
lsp_health()
```

**Reports:**
- Server status (Running/Stopped)
- Process ID (PID)
- Restart count
- Launch command

### lsp_rename

Rename a symbol across the workspace.

```
lsp_rename(file_path, line, character, new_name)
```

---

## Session Management

### session_list

List available Claude Code sessions.

```
session_list()
```

### session_read

Read content from a session.

```
session_read(session_id)
```

### session_search

Search across sessions.

```
session_search(query)
```

---

## Skills

### skill_list

List available slash commands/skills.

```
skill_list()
```

### skill_get

Get content of a specific skill.

```
skill_get(skill_name)
```

### Built-in Skills (Slash Commands)

Stravinsky provides several pre-defined skills accessible via slash commands:

| Skill | Purpose |
|-------|---------|
| `/stravinsky` | Orchestrate complex tasks with parallel agent delegation |
| `/plan` | Create implementation plans before coding (uses Opus) |
| `/delphi` | Consult strategic advisor for architecture/debugging |
| `/dewey` | Research documentation and implementation examples |
| `/verify` | Post-implementation verification checklist |
| `/review` | Structured code review workflow |
| `/debug` | Systematic debugging with root cause analysis |
| `/get-context` | Refresh Git status, rules, and todos |
| `/health` | Comprehensive system health check |

**Example Usage:**
```
/plan Add OAuth2 authentication with Google and GitHub providers
/review changes to src/auth/
/debug Error: Connection refused on port 5432
```

---

## Parallel Execution Patterns

### Pattern 1: Parallel Exploration

```
1. agent_spawn("Find all database models", "explore", "DB models")
2. agent_spawn("Find all API routes", "explore", "API routes")
3. agent_spawn("Find all test files", "explore", "Tests")
4. Wait for all with agent_output
```

### Pattern 2: Research + Implementation

```
1. agent_spawn("Research best practices for X", "dewey", "Research")
2. Wait for research with agent_output
3. agent_spawn("Implement based on research", "frontend", "Implement")
```

### Pattern 3: IRONSTAR Mode

For maximum parallelism, spawn 5+ agents simultaneously:

```
1. agent_spawn("Task 1", "explore", "T1")
2. agent_spawn("Task 2", "explore", "T2")
3. agent_spawn("Task 3", "dewey", "T3")
4. agent_spawn("Task 4", "frontend", "T4")
5. agent_spawn("Task 5", "delphi", "T5")
6. Monitor all with agent_list
7. Collect with agent_output for each
```

---

## Best Practices

1. **Always use parallel agents** for multi-step tasks
2. **Match agent type to task** - explore for search, dewey for docs
3. **Use thinking_budget** for complex reasoning tasks
4. **Monitor with agent_progress** for long-running tasks
5. **Cancel stuck agents** with agent_cancel
