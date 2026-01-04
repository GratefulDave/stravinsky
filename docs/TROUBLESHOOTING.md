# Troubleshooting Stravinsky

Common issues and solutions.

---

## Installation Issues

### "stravinsky" command not found

**Solution:**
```bash
# Reinstall
uv tool install stravinsky --force

# Or use uvx directly
uvx stravinsky --help
```

### MCP server not appearing in Claude Code

**Solution:**
```bash
# Remove and re-add
claude mcp remove stravinsky
claude mcp add stravinsky -- uvx stravinsky

# Verify
claude mcp list
```

### "uvx: command not found"

**Solution:**
```bash
# Install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal, then
claude mcp add stravinsky -- uvx stravinsky
```

---

## Authentication Issues

### Gemini: 403 Forbidden

**Causes:**
- Token expired
- Invalid authentication

**Solution:**
```bash
stravinsky-auth logout gemini
stravinsky-auth login gemini
```

### OpenAI: Port 1455 in use

**Cause:** Codex CLI uses the same port

**Solution:**
```bash
# Stop Codex CLI
killall codex

# Retry login
stravinsky-auth login openai
```

### OpenAI: Authentication failed

**Causes:**
- No ChatGPT Plus/Pro subscription
- Token expired

**Solution:**
1. Ensure you have ChatGPT Plus or Pro
2. Re-authenticate:
```bash
stravinsky-auth logout openai
stravinsky-auth login openai
```

### Token refresh fails

**Solution:**
```bash
# Clear and re-authenticate
stravinsky-auth logout gemini
stravinsky-auth logout openai
stravinsky-auth login gemini
stravinsky-auth login openai
```

---

## Runtime Issues

### invoke_gemini returns empty response

**Possible causes:**
- Model rate limited
- Token invalid

**Solution:**
1. Check auth status: `stravinsky-auth status`
2. Re-authenticate if needed
3. Try with smaller `max_tokens`

### Agents not spawning

**Possible causes:**
- Claude Code CLI not available
- Permission issues

**Solution:**
```bash
# Verify claude is available
which claude

# Check MCP status
claude mcp list
```

### Agent timeout

**Solution:**
1. Check agent progress: `agent_progress(task_id)`
2. Cancel if stuck: `agent_cancel(task_id)`
3. Retry with more specific prompt

### "All Antigravity endpoints failed"

**Cause:** Network or auth issues with Gemini API

**Solution:**
```bash
# Re-authenticate
stravinsky-auth logout gemini
stravinsky-auth login gemini
```

---

## Performance Issues

### Slow startup

**Cause:** uvx downloads on first run

**Solution:** Install globally instead:
```bash
uv tool install stravinsky
claude mcp remove stravinsky
claude mcp add stravinsky -- stravinsky
```

### Agents running slowly

**Tips:**
1. Use `explore` agent for quick searches
2. Use specific prompts
3. Cancel long-running agents
4. Reduce parallel agent count if system is overloaded

---

## MCP Communication Issues

### "MCP server disconnected"

**Solutions:**
1. Restart Claude Code
2. Check if stravinsky process is running
3. Re-add MCP server:
```bash
claude mcp remove stravinsky
claude mcp add stravinsky -- uvx stravinsky
```

### Tools not appearing

**Solutions:**
1. Wait a few seconds after starting Claude Code
2. Restart Claude Code
3. Verify MCP is added: `claude mcp list`

---

## Getting Help

### Check Logs

```bash
# MCP server logs (if running globally)
ps aux | grep stravinsky
```

### Report Issues

- GitHub: https://github.com/GratefulDave/stravinsky/issues

### Debug Mode

Set environment variable for verbose output:
```bash
STRAVINSKY_DEBUG=1 stravinsky
```

---

## FAQ

**Q: Do I need both Gemini and OpenAI auth?**
A: No. Each is optional. Use whichever you need.

**Q: Can I use Stravinsky without authentication?**
A: Agent tools work without auth. Model invocation requires auth.

**Q: How do I update Stravinsky?**
A: With uvx, it auto-updates. With uv tool: `uv tool upgrade stravinsky`

**Q: Where are tokens stored?**
A: In your system keyring (secure storage).

**Q: Can multiple projects use the same installation?**
A: Yes. Install once globally, use everywhere.
