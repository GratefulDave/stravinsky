# Stravinsky Installation & Removal Guide

Complete installation, configuration, and removal instructions for Stravinsky MCP Bridge.

---

## Table of Contents

- [Installation](#installation)
  - [Method 1: One-Shot with uvx (Recommended)](#method-1-one-shot-with-uvx-recommended)
  - [Method 2: Global Installation with uv](#method-2-global-installation-with-uv)
  - [Method 3: From Source (Development)](#method-3-from-source-development)
- [Authentication Setup](#authentication-setup)
- [Project Initialization](#project-initialization)
- [Verification](#verification)
- [Removal](#removal)
  - [Complete Uninstall](#complete-uninstall)
  - [Remove from Specific Project](#remove-from-specific-project)
  - [Remove Authentication Tokens Only](#remove-authentication-tokens-only)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Method 1: One-Shot with uvx (Recommended)

**Zero installation needed!** Claude Code will automatically download and run Stravinsky on demand.

```bash
# Add to Claude Code MCP configuration
claude mcp add stravinsky -- uvx stravinsky
```

**Pros:**
- No manual installation
- Always uses latest version
- Automatic dependency management
- Minimal disk usage

**Cons:**
- Slightly slower first startup (downloads package)

---

### Method 2: Global Installation with uv

Install Stravinsky globally for faster startup times.

```bash
# Install globally
uv tool install stravinsky

# Add to Claude Code
claude mcp add stravinsky -- stravinsky
```

**Pros:**
- Faster startup (pre-installed)
- Offline usage after installation
- Version pinning

**Cons:**
- Requires manual updates: `uv tool install --upgrade stravinsky`

---

### Method 3: From Source (Development)

For contributors or testing unreleased features.

```bash
# Clone repository
git clone https://github.com/GratefulDave/stravinsky.git
cd stravinsky

# Install in development mode
uv tool install --editable .

# Add to Claude Code
claude mcp add stravinsky -- stravinsky
```

---

## Authentication Setup

Stravinsky supports **Google (Gemini)** and **OpenAI (ChatGPT)** authentication.

### Authenticate with Google (Gemini)

```bash
stravinsky-auth login gemini
```

Opens browser for OAuth authentication. Credentials stored securely in system keyring.

### Authenticate with OpenAI (ChatGPT Plus/Pro)

```bash
stravinsky-auth login openai
```

**Requirements:**
- ChatGPT Plus or Pro subscription
- Port 1455 available (used by OAuth callback)

### Check Authentication Status

```bash
stravinsky-auth status
```

Example output:
```
Authentication Status:

  Gemini: ✓ Authenticated
    Expires in: 2h 30m
  Openai: ✗ Not authenticated
```

### Refresh Tokens

Tokens auto-refresh, but you can manually refresh:

```bash
stravinsky-auth refresh gemini
stravinsky-auth refresh openai
```

---

## Project Initialization

Bootstrap any repository for Stravinsky usage:

```bash
# Navigate to your project
cd /path/to/your/project

# Initialize Stravinsky
stravinsky-auth init
```

**This creates:**

1. **`.claude/commands/`** - Slash commands:
   - `/stravinsky` - Orchestrator
   - `/delphi` - Strategic advisor
   - `/dewey` - Documentation researcher
   - `/context` - Git/rules/todo context
   - `/health` - System health check
   - `/list` - List background agents
   - `/parallel` - Parallel execution
   - `/version` - Version info

2. **`CLAUDE.md`** - Updated with Stravinsky usage instructions

---

## Verification

### 1. Check Installation

```bash
# Check if installed
uv tool list | grep stravinsky

# Check version
stravinsky --version
```

### 2. Verify MCP Registration

```bash
# List MCP servers in Claude Code
claude mcp list
```

Should show `stravinsky` in the list.

### 3. Test Authentication

```bash
stravinsky-auth status
```

### 4. Test in Claude Code

Start a conversation in Claude Code and try:

```
Can you list the Stravinsky tools available?
```

Claude should respond with the list of 31 MCP tools.

---

## Removal

### Complete Uninstall

Remove Stravinsky entirely from your system.

#### Step 1: Remove from Claude Code

```bash
claude mcp remove stravinsky
```

#### Step 2: Uninstall Package

**If installed with uvx:**
```bash
# Nothing to uninstall - uvx downloads on-demand
# Removal from Claude Code is sufficient
```

**If installed globally with uv:**
```bash
uv tool uninstall stravinsky
```

**If installed from source:**
```bash
uv tool uninstall stravinsky
# Optionally delete cloned repository
rm -rf /path/to/stravinsky
```

#### Step 3: Remove Authentication Tokens

```bash
# Logout from both providers
stravinsky-auth logout gemini
stravinsky-auth logout openai
```

#### Step 4: Remove Project Configurations (Optional)

```bash
# Remove from each project where you ran 'stravinsky-auth init'
cd /path/to/project
rm -rf .claude/commands/stravinsky/
rm -rf .claude/commands/delphi/
rm -rf .claude/commands/dewey/
rm -rf .claude/commands/context/
rm -rf .claude/commands/health/
rm -rf .claude/commands/list/
rm -rf .claude/commands/parallel/
rm -rf .claude/commands/version/

# Manually remove Stravinsky sections from CLAUDE.md
# (Edit file and remove sections added by init)
```

#### Step 5: Clean System Keyring (Optional)

Tokens are stored in your system keyring. To verify removal:

**macOS:**
```bash
# Open Keychain Access app
# Search for "stravinsky"
# Delete any found entries
```

**Linux:**
```bash
# Using secret-tool (if available)
secret-tool clear service stravinsky
```

**Windows:**
```powershell
# Tokens stored in Windows Credential Manager
# Open: Control Panel → Credential Manager
# Remove entries containing "stravinsky"
```

---

### Remove from Specific Project

Keep Stravinsky installed but remove from one project.

```bash
cd /path/to/project

# Remove slash commands
rm -rf .claude/commands/stravinsky/
rm -rf .claude/commands/delphi/
rm -rf .claude/commands/dewey/
rm -rf .claude/commands/context/
rm -rf .claude/commands/health/

# Edit CLAUDE.md manually to remove Stravinsky instructions
```

---

### Remove Authentication Tokens Only

Keep Stravinsky installed but clear credentials.

```bash
# Remove specific provider
stravinsky-auth logout gemini
stravinsky-auth logout openai

# Verify removal
stravinsky-auth status
```

Output should show:
```
Authentication Status:

  Gemini: ✗ Not authenticated
  Openai: ✗ Not authenticated
```

---

## Troubleshooting

### "stravinsky: command not found"

**Cause:** Stravinsky not installed or not in PATH.

**Solution:**
```bash
# If using uvx, this is expected (Claude Code handles it)
# If using uv tool install, ensure ~/.local/bin is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Or reinstall
uv tool install stravinsky
```

### "Port 1455 already in use" (OpenAI login)

**Cause:** Codex CLI or another process using port 1455.

**Solution:**
```bash
# Find process
lsof -i :1455

# Kill Codex CLI if running
killall codex

# Retry login
stravinsky-auth login openai
```

### "OAuth failed" (Gemini/OpenAI)

**Cause:** Network issues, invalid credentials, or expired session.

**Solution:**
```bash
# Clear existing token
stravinsky-auth logout gemini  # or openai

# Retry login
stravinsky-auth login gemini   # or openai
```

### "MCP server not responding"

**Cause:** Stravinsky process crashed or not started.

**Solution:**
```bash
# Check Claude Code logs
claude mcp logs stravinsky

# Restart Claude Code
# The MCP server will auto-restart
```

### "Token expired" messages

**Cause:** Access token expired and auto-refresh failed.

**Solution:**
```bash
# Manually refresh
stravinsky-auth refresh gemini  # or openai

# Or re-login
stravinsky-auth login gemini    # or openai
```

### Can't find `.claude/commands/` after init

**Cause:** Wrong directory or init failed.

**Solution:**
```bash
# Ensure you're in project root
pwd

# Re-run init with verbose output
stravinsky-auth init

# Check for error messages
```

---

## Dependencies

All dependencies are automatically installed:

- `mcp>=1.2.1`
- `pydantic>=2.0.0`
- `httpx>=0.24.0`
- `python-dotenv>=1.0.0`
- `google-auth-oauthlib>=1.0.0`
- `google-auth>=2.20.0`
- `openai>=1.0.0`
- `cryptography>=41.0.0`
- `rich>=13.0.0`
- `aiofiles>=23.1.0`
- `psutil>=5.9.0`
- `keyring>=25.7.0`
- `jedi>=0.19.2`
- `ruff>=0.14.10`
- `tenacity>=8.5.0`

**You don't need to install anything manually.**

---

## Getting Help

- **Documentation:** [README.md](./README.md)
- **Issues:** [GitHub Issues](https://github.com/GratefulDave/stravinsky/issues)
- **Claude Code Docs:** [Claude Code MCP Guide](https://docs.anthropic.com/claude/docs/model-context-protocol)

---

## Quick Reference

### Installation
```bash
# Recommended: uvx
claude mcp add stravinsky -- uvx stravinsky

# OR: Global install
uv tool install stravinsky
claude mcp add stravinsky -- stravinsky
```

### Authentication
```bash
stravinsky-auth login gemini      # Google OAuth
stravinsky-auth login openai      # OpenAI OAuth
stravinsky-auth status            # Check status
stravinsky-auth logout <provider> # Remove credentials
```

### Project Setup
```bash
cd /path/to/project
stravinsky-auth init              # Create slash commands + update CLAUDE.md
```

### Complete Removal
```bash
claude mcp remove stravinsky      # Remove from Claude Code
uv tool uninstall stravinsky      # Uninstall package
stravinsky-auth logout gemini     # Clear credentials
stravinsky-auth logout openai
```

---

**Last Updated:** v0.2.34  
**License:** MIT
