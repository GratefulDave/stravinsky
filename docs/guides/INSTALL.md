# Installing Stravinsky MCP

Complete guide to installing and configuring Stravinsky in your projects.

## Quick Start (Recommended)

### One-Line Installation

```bash
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest
```

This installs Stravinsky as an MCP server for Claude Code using `uvx` (no global installation needed).

**Why Python 3.13 is required:** Stravinsky depends on chromadb, which uses onnxruntime. The onnxruntime package does not have pre-built wheels for Python 3.14+, so Python 3.11-3.13 is required.

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
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest
```

**Pros:** No global packages, always latest version
**Cons:** Slightly slower startup (downloads on first run)

**Python Version:** Requires Python 3.11-3.13 (chromadb/onnxruntime limitation)

### Method 2: Global Tool Installation

Best for: Daily use, faster startup, offline availability.

```bash
# Install globally with uv (specify Python 3.13)
uv tool install --python python3.13 stravinsky

# Add to Claude Code
claude mcp add --scope user stravinsky -- stravinsky
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

**Python Version:** Requires Python 3.11-3.13 (chromadb/onnxruntime limitation)

### Method 3: Development Installation

Best for: Contributing, customizing, debugging.

```bash
# Clone the repository
git clone https://github.com/GratefulDave/stravinsky.git
cd stravinsky

# Install in editable mode with pip
uv pip install -e .

# Add to Claude Code
claude mcp add --scope user stravinsky -- stravinsky
```

**Python Version:** Requires Python 3.11-3.13 (chromadb/onnxruntime limitation)

---

## Authentication Setup

Stravinsky uses OAuth 2.0 with PKCE (Proof Key for Code Exchange) to authenticate with external AI providers. All tokens are stored securely in your system keyring and automatically refresh when needed.

### Gemini (Google AI)

```bash
stravinsky-auth login gemini
```

**OAuth Flow:**
1. Opens browser to Google OAuth consent screen
2. Uses PKCE (S256) for secure public client authentication
3. Redirects to local callback handler after approval
4. Exchanges authorization code for access/refresh tokens
5. Stores tokens in system keyring (`stravinsky-gemini`)

**Requirements:**
- A Google account
- Access to Google Antigravity API (Gemini backend)
- Browser access for OAuth consent

**Token Management:**
- Access tokens auto-refresh 5 minutes before expiry
- Refresh tokens stored persistently in system keyring
- No manual token management required

**Storage Location:**
- macOS: Keychain
- Linux: Secret Service API
- Windows: Credential Locker

### API Key Fallback (Gemini)

For high-volume usage or when OAuth rate limits are exhausted, configure an API key as a fallback.

**Setup:**
Add `GEMINI_API_KEY` to your `.env` file in the project root:

```bash
# .env file
GEMINI_API_KEY=your_api_key_here

# Or use GOOGLE_API_KEY (same effect)
GOOGLE_API_KEY=your_api_key_here
```

**Get your API key:** Visit [Google AI Studio](https://aistudio.google.com/app/apikey)

**Rate Limit Architecture:**
- **OAuth**: Lower rate limits, but convenient (no API key management)
- **API Key**: Tier 3 high quotas - automatic fallback for heavy usage

**Auth Priority:**
1. OAuth is tried first (if configured)
2. On OAuth 429 rate limit - automatically switch to API key for 5 minutes
3. After 5-minute cooldown - retry OAuth

### OpenAI (ChatGPT)

```bash
stravinsky-auth login openai
```

**OAuth Flow:**
1. Opens browser to ChatGPT OAuth consent screen
2. Uses PKCE (S256) with identical flow to Codex CLI
3. **Requires port 1455 for callback** (same as Codex CLI)
4. Exchanges authorization code for access/refresh tokens
5. Stores tokens in system keyring (`stravinsky-openai`)

**Requirements:**
- **ChatGPT Plus or Pro subscription** (required)
- Port 1455 available for OAuth callback
- Browser access for OAuth consent
- No Codex CLI running on same port

**OAuth Implementation:**
Stravinsky replicates the `opencode-openai-codex-auth` plugin:
- Client ID: `app_EMoamEEZ73f0CkXaXp7hrann` (official Codex OAuth client)
- Endpoint: `https://auth.openai.com/oauth/authorize`
- Callback: `http://localhost:1455/auth/callback`
- Scope: `openid profile email offline_access`

**Token Management:**
- Access tokens auto-refresh 5 minutes before expiry
- JWT tokens contain account ID for backend attribution
- Refresh tokens stored persistently in system keyring
- Compatible with Codex CLI tokens (can share authentication)

**Port 1455 Requirement:**
OpenAI's OAuth requires this specific port for the callback. If the port is in use:
```bash
# Check what's using port 1455
lsof -i :1455

# Stop Codex CLI if running
killall codex

# Then retry login
stravinsky-auth login openai
```

### Check Status

```bash
stravinsky-auth status
```

Shows:
- Authentication status for each provider (✓ Authenticated / ✗ Not authenticated)
- Token expiry information
- Account details (email for Gemini, account ID for OpenAI)

### Logout

```bash
stravinsky-auth logout gemini
stravinsky-auth logout openai
```

Removes tokens from system keyring. You'll need to re-authenticate to use the respective provider.

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

- `stravinsky` - Task orchestration and complex workflows
- `planner` - Pre-implementation planning with Claude Opus
- `explore` - Codebase search, "where is X?" questions
- `dewey` - Documentation research, implementation examples
- `frontend` - UI/UX work, component design
- `delphi` - Strategic advice, architecture review
- `document_writer` - Technical documentation writing
- `multimodal` - Visual analysis of screenshots and diagrams

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
# Remove and re-add (with Python 3.13)
claude mcp remove stravinsky
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest
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
stravinsky --version
```

---

## Available Commands

| Command | Description |
|---------|-------------|
| `stravinsky` | Start the MCP server |
| `stravinsky --version` | Check installed version |
| `stravinsky-auth` | Authentication CLI |
| `stravinsky-proxy` | Start proxy mode for long-running generations |

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
