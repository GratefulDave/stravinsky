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
- 🛠️ **31 MCP Tools** - Model invocation, code search, LSP integrations, session management, and more
- 🧠 **7 Specialized Agents** - Stravinsky (orchestrator), Delphi (advisor), Dewey (documentation), and more
- 🔄 **Background Tasks** - Spawn parallel agents with full tool access via Claude Code CLI
- 📝 **LSP Integration** - Full Language Server Protocol support for Python (jedi)
- 🔍 **AST-Aware Search** - Structural code search and refactoring with ast-grep

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

## Add to Your CLAUDE.md

After installing globally, add this to your project's `CLAUDE.md`:

```markdown
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

1. **Immediately use agent_spawn** for each independent component
2. Fire all agents simultaneously, don't wait
3. Monitor with agent_progress, collect with agent_output

### ULTRATHINK / ULTRAWORK

- **ULTRATHINK**: Engage exhaustive deep reasoning, multi-dimensional analysis
- **ULTRAWORK**: Maximum parallel execution - spawn agents aggressively for every subtask
```

## Tools (31)

| Category         | Tools                                                                              |
| ---------------- | ---------------------------------------------------------------------------------- |
| **Model Invoke** | `invoke_gemini`, `invoke_openai`, `get_system_health`                              |
| **Environment**  | `get_project_context`, `task_spawn`, `task_status`, `task_list`                    |
| **Agents**       | `agent_spawn`, `agent_output`, `agent_cancel`, `agent_list`, `agent_progress`      |
| **Code Search**  | `ast_grep_search`, `ast_grep_replace`, `grep_search`, `glob_files`                 |
| **LSP**          | `lsp_diagnostics`, `lsp_hover`, `lsp_goto_definition`, `lsp_find_references`, etc. |
| **Sessions**     | `session_list`, `session_read`, `session_search`                                   |
| **Skills**       | `skill_list`, `skill_get`                                                          |

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
├── mcp_bridge/           # Python MCP server
│   ├── server.py         # Entry point
│   ├── auth/             # OAuth (Google & OpenAI)
│   ├── tools/            # Model invoke, search, skills
│   ├── prompts/          # Agent system prompts
│   └── config/           # Bridge configuration
├── pyproject.toml        # Build system
└── README.md             # This file
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
