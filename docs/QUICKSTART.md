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

## Step 3: Add to Your Project

Create or update `CLAUDE.md` in your project root:

```markdown
## Stravinsky MCP

Use Stravinsky for parallel agent execution.

### Quick Commands
- `agent_spawn(prompt, agent_type, description)` - Spawn agent
- `agent_output(task_id)` - Get results
- `agent_list()` - See all agents

### Agent Types
- `explore` - Search codebase
- `dewey` - Research docs
- `delphi` - Strategic advice
- `frontend` - UI work
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

```
Spawn 3 explore agents in parallel:
1. Find all database models
2. Find all API routes
3. Find all test files
```

---

## Next Steps

- Read [INSTALL.md](INSTALL.md) for detailed installation options
- Read [USAGE.md](USAGE.md) for complete tool reference
- Read [AGENTS.md](AGENTS.md) for agent type details
