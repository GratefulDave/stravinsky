# Stravinsky Documentation

## Quick Links

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Get running in 2 minutes |
| [INSTALL.md](INSTALL.md) | Detailed installation guide |
| [USAGE.md](USAGE.md) | Complete tool reference |
| [AGENTS.md](AGENTS.md) | Agent type details |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues & solutions |

## TL;DR

```bash
# Install
claude mcp add stravinsky -- uvx stravinsky

# Authenticate
stravinsky-auth login gemini
stravinsky-auth login openai

# Use in Claude Code
"Spawn an explore agent to find all API endpoints"
```

## What is Stravinsky?

Stravinsky is an MCP (Model Context Protocol) server that extends Claude Code with:

- **Multi-model invocation** - Call Gemini and OpenAI from Claude
- **Parallel agents** - Spawn background agents with full tool access
- **Code search** - AST-aware search and LSP integration
- **Session management** - Access Claude Code sessions

## Support

- GitHub Issues: https://github.com/GratefulDave/stravinsky/issues
- PyPI: https://pypi.org/project/stravinsky/
