# Installing Stravinsky MCP

Complete guide to installing and configuring Stravinsky in your projects.

## Quick Start (Recommended)

### One-Line Installation

```bash
claude mcp add stravinsky -- uvx stravinsky
```

This installs Stravinsky as an MCP server for Claude Code using `uvx` (no global installation needed).

### Verify Installation

```bash
claude mcp list
```

You should see `stravinsky` in the list of MCP servers.

---

## Installation Methods

### Method 1: uvx (Zero Installation)

Best for: Quick setup, trying Stravinsky, CI/CD environments.

```bash
# Add to Claude Code (runs via uvx each time)
claude mcp add stravinsky -- uvx stravinsky
```

**Pros:** No global packages, always latest version
**Cons:** Slightly slower startup (downloads on first run)

### Method 2: Global Tool Installation

Best for: Daily use, faster startup, offline availability.

```bash
# Install globally with uv
uv tool install stravinsky

# Add to Claude Code
claude mcp add stravinsky -- stravinsky
```

**Upgrade:**
```bash
uv tool upgrade stravinsky
```

**Uninstall:**
```bash
uv tool uninstall stravinsky
claude mcp remove stravinsky
```

### Method 3: Development Installation

Best for: Contributing, customizing, debugging.

```bash
# Clone the repository
git clone https://github.com/GratefulDave/stravinsky.git
cd stravinsky

# Install in editable mode
uv tool install --editable .

# Add to Claude Code
claude mcp add stravinsky -- stravinsky
```

---

## Authentication Setup

Stravinsky uses OAuth to authenticate with external AI providers.

### Gemini (Google AI)

```bash
stravinsky-auth login gemini
```

This opens a browser for Google OAuth. You need:
- A Google account
- Access to Gemini API (via Google AI Studio or Cloud)

### OpenAI (ChatGPT)

```bash
stravinsky-auth login openai
```

This opens a browser for OpenAI OAuth. You need:
- A ChatGPT Plus or Pro subscription
- Port 1455 available (stop Codex CLI if running: `killall codex`)

### Check Status

```bash
stravinsky-auth status
```

### Logout

```bash
stravinsky-auth logout gemini
stravinsky-auth logout openai
```

---

## Project Configuration

### Add to Your Project's CLAUDE.md

Create or update your project's `CLAUDE.md` file:

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

### Add Slash Commands (Optional)

Create `.claude/commands/stravinsky.md` in your project:

```markdown
# Stravinsky Orchestrator

Invoke the Stravinsky orchestrator for complex multi-step tasks.

When this skill is triggered:
1. Analyze the task and break it into independent components
2. Spawn parallel agents for each component
3. Monitor progress and collect results
4. Synthesize final output

Use ULTRAWORK mode for maximum parallelism.
```

---

## Verifying the Installation

### 1. Check MCP Server Status

```bash
claude mcp list
```

### 2. Test in Claude Code

Start Claude Code and try:

```
Use invoke_gemini to say hello
```

Or:

```
Use agent_spawn to explore this codebase
```

### 3. Check Auth Status

```bash
stravinsky-auth status
```

---

## Troubleshooting

### "stravinsky" command not found

```bash
# Reinstall the tool
uv tool install stravinsky --force

# Or use uvx directly
uvx stravinsky --help
```

### MCP Server Not Loading

```bash
# Remove and re-add
claude mcp remove stravinsky
claude mcp add stravinsky -- uvx stravinsky
```

### OpenAI "Port 1455 in use"

```bash
# Stop Codex CLI
killall codex

# Then retry login
stravinsky-auth login openai
```

### Gemini 403 Errors

Ensure you're authenticated:
```bash
stravinsky-auth logout gemini
stravinsky-auth login gemini
```

### Token Expired

Tokens refresh automatically, but if issues persist:
```bash
stravinsky-auth logout gemini
stravinsky-auth login gemini
```

---

## Updating Stravinsky

### With uvx (automatic)

uvx always uses the latest version. No action needed.

### With uv tool

```bash
uv tool upgrade stravinsky
```

### Check Version

```bash
uvx stravinsky --version
# or
stravinsky --version
```

---

## Uninstalling

### Remove from Claude Code

```bash
claude mcp remove stravinsky
```

### Remove Global Installation

```bash
uv tool uninstall stravinsky
```

### Clear Auth Tokens

```bash
stravinsky-auth logout gemini
stravinsky-auth logout openai
```

---

## Next Steps

- Read the [Usage Guide](USAGE.md) for detailed tool documentation
- See [Agent Types](AGENTS.md) for specialized agent configurations
- Check [Troubleshooting](TROUBLESHOOTING.md) for common issues
