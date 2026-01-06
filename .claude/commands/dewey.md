---
description: Research librarian - docs, OSS implementations, GitHub examples.
---
# Dewey - Research Librarian

Invokes the dewey agent (gemini-3-flash) for multi-source research.

Equivalent to oh-my-opencode's `librarian` agent.

## Usage

```
/dewey <research question>
```

## Capabilities

- Official documentation lookup (Context7)
- GitHub code search (grep.app)
- Web search for best practices (Exa)
- OSS implementation examples with permalinks
- Multi-repository analysis

## Instructions

Spawn the dewey agent for comprehensive research:

```python
stravinsky_agent_spawn(
    prompt="""$ARGUMENTS

Research this topic using ALL available sources:
1. Official documentation via Context7
2. GitHub code examples via grep.app  
3. Web search for current best practices via Exa
4. Clone relevant repos if needed for deep analysis

REQUIREMENTS:
- Provide GitHub permalinks for code citations
- Include version/date context
- Synthesize findings with evidence links
- Note any conflicting information""",
    agent_type="dewey",
    description="Research: $ARGUMENTS"
)
```

The dewey agent uses gemini-3-flash and has access to:
- `MCP_DOCKER_web_search_exa` - Real-time web search
- `context7_query-docs` - Official library documentation
- `gh` CLI - GitHub operations
- `grep_search` / `ast_grep_search` - Code search

$ARGUMENTS
