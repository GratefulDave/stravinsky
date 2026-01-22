# Stravinsky Quick Start

Get up and running with Stravinsky in 2 minutes.

---

## Step 1: Install

```bash
# Recommended (user-scoped with Python 3.13)
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest
```

**Note:** Python 3.11-3.13 is required (chromadb/onnxruntime limitation).

## Step 2: Authenticate

```bash
# For Gemini (Google AI)
stravinsky-auth login gemini

# For OpenAI (requires ChatGPT Plus/Pro)
stravinsky-auth login openai

# Check authentication status
stravinsky-auth status
```

### API Key Fallback (Optional)

For high-volume usage, add a Gemini API key to your `.env` file:

```bash
# .env file in project root
GEMINI_API_KEY=your_api_key_here
```

This provides automatic fallback when OAuth rate limits are reached.

## Step 3: Verify Installation

```bash
# Check version
stravinsky --version

# List MCP servers
claude mcp list
```

You should see `stravinsky` in the list of MCP servers.

## Step 4: Initialize Project Routing (Optional)

Create a project-local routing configuration to optimize model usage for different tasks:

```bash
stravinsky-auth routing init
```

This creates `.stravinsky/routing.json` with default rules for code generation, debugging, and search.

## Step 5: Add to Your Project

Create or update `CLAUDE.md` in your project root:

```markdown
## Stravinsky MCP

Use Stravinsky for parallel agent execution.

### Quick Commands
- `agent_spawn(prompt, agent_type, description)` - Spawn agent
- `agent_output(task_id)` - Get results
- `agent_list()` - See all agents

### Agent Types
- `stravinsky` - Orchestrate complex tasks
- `planner` - Pre-implementation planning
- `explore` - Search codebase
- `dewey` - Research docs
- `delphi` - Strategic advice
- `frontend` - UI work
- `document_writer` - Write technical docs
- `multimodal` - Analyze screenshots/diagrams
```

## Step 6: Use It

Start Claude Code in your project and try:

```
Spawn an explore agent to find all API endpoints in this project
```

Or:

```
Use invoke_gemini to explain the architecture of this codebase
```

---

## Common Tasks

### Search the Codebase

```
Use agent_spawn with prompt "Find all functions that handle authentication"
and agent_type "explore"
```

### Get Documentation Help

```
Use agent_spawn with prompt "Find examples of using React Query with pagination"
and agent_type "dewey"
```

### Invoke AI Models Directly

```
Use invoke_gemini with prompt "Review this code for security issues: [paste code]"
```

### Parallel Execution

Spawn multiple agents simultaneously for maximum efficiency:

```
# Spawn 3 explore agents in parallel
explore_models = agent_spawn("Find all database models", "explore", "Models")
explore_api = agent_spawn("Find all API routes", "explore", "Routes")
explore_tests = agent_spawn("Find all test files", "explore", "Tests")

# Monitor progress
agent_list()

# Collect results
models = agent_output(explore_models)
api = agent_output(explore_api)
tests = agent_output(explore_tests)
```

### ULTRAWORK / ULTRATHINK

For complex tasks, use special modes:
- **ULTRAWORK**: Maximum parallel execution - spawn agents for every subtask
- **ULTRATHINK**: Extended reasoning with high thinking_budget for complex problems

### Slash Commands

Quick access to common workflows:
```
/stravinsky - Task orchestration
/delphi - Strategic advice
/dewey - Documentation research
/get-context - Refresh Git/rules/todos
```

---

## Available Commands

| Command | Description |
|---------|-------------|
| `stravinsky` | Start the MCP server |
| `stravinsky --version` | Check installed version |
| `stravinsky-auth` | Authentication CLI |
| `stravinsky-proxy` | Start proxy mode |

---

## Next Steps

- Read [INSTALL.md](INSTALL.md) for detailed installation options
- Read [USAGE.md](USAGE.md) for complete tool reference
- Read [AGENTS.md](AGENTS.md) for agent type details
