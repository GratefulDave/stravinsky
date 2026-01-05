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

- **Multi-model invocation** - Call Gemini and OpenAI from Claude with OAuth
- **Multimodal vision** - Analyze screenshots, diagrams, and PDFs with Gemini vision API
- **Agent context logging** - Track model invocations with automatic agent metadata
- **Parallel agents** - Spawn background agents with full tool access
- **Code search** - AST-aware search and LSP integration
- **Session management** - Access Claude Code sessions

## Key Features

### Multimodal Vision Support

Stravinsky enables visual analysis through Gemini's vision API:

```
invoke_gemini(
    prompt="Analyze this screenshot for accessibility issues",
    image_path="/path/to/screenshot.png",
    agent_context={"agent_type": "multimodal"}
)
```

**Supported formats:** PNG, JPG, JPEG, GIF, WEBP, PDF (< 20MB)

**Use cases:**
- Screenshot analysis for UI/UX feedback
- Diagram interpretation and documentation
- PDF data extraction
- Visual debugging

### Agent Context Logging

All model invocations can include agent metadata for better tracking:

```
[explore] → gemini-3-flash: Find all database models...
[delphi] → gpt-5.2-codex: Review this architecture...
```

This provides visibility into:
- Which agent made which request
- Model usage by agent type
- Token consumption patterns
- Execution tracing

## Support

- GitHub Issues: https://github.com/GratefulDave/stravinsky/issues
- PyPI: https://pypi.org/project/stravinsky/
- Version: 0.2.58
