# Stravinsky Quick Start

Get up and running with Stravinsky in 2 minutes.

---

## Step 1: Install

```bash
claude mcp add stravinsky -- uvx stravinsky
```

## Step 2: Authenticate

```bash
# For Gemini (Google AI)
stravinsky-auth login gemini

# For OpenAI (requires ChatGPT Plus/Pro)
stravinsky-auth login openai
```

## Step 3: Initialize Project Routing

Create a project-local routing configuration to optimize model usage for different tasks:

```bash
stravinsky-auth routing init
```

This creates `.stravinsky/routing.json` with default rules for code generation, debugging, and search.

## Step 4: Add to Your Project

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

## Step 4: Use It

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

## Next Steps

- Read [INSTALL.md](INSTALL.md) for detailed installation options
- Read [USAGE.md](USAGE.md) for complete tool reference
- Read [AGENTS.md](AGENTS.md) for agent type details
