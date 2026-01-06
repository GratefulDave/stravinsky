# Model Routing Architecture

## The Problem

Claude Code's native Task system only supports Claude models. To use Gemini/GPT, agents must call MCP tools (invoke_gemini, invoke_openai).

## Alternatives Considered

### Option A: Pure Native (Task only)
- All agents run on Claude Sonnet
- Agents call invoke_gemini/invoke_openai for specific tasks
- **Problem**: Double cost - paying for Sonnet + Gemini for every exploration task
- **Rejected**: Too expensive for high-volume exploration work

### Option B: Pure MCP (agent_spawn only)
- Use Stravinsky MCP's agent_spawn tool for all delegation
- Agents run as subprocess, call Gemini/GPT directly
- **Problem**: Subprocess overhead, slower startup, no Task parallelism benefits
- **Rejected**: Slower and more complex than necessary

### Option C: Thin Wrapper (CHOSEN)
- Use Task to spawn cheap Claude Haiku agents
- Haiku agents immediately delegate to invoke_gemini/invoke_openai
- Haiku does NO actual work - just parses request and delegates
- **Benefits**:
  - Fast (in-process Task execution)
  - Cheap (Haiku is 1/10th Sonnet cost)
  - Simple (clear single-responsibility pattern)
  - Compatible (works with Claude Code's existing Task infrastructure)

## Cost Analysis

| Approach | Wrapper Cost | Work Cost | Total |
|----------|--------------|-----------|-------|
| Pure Native (Sonnet→Gemini) | $3/1M tokens | $0.075/1M | $3.075/1M |
| Thin Wrapper (Haiku→Gemini) | $0.25/1M tokens | $0.075/1M | $0.325/1M |
| **Savings** | | | **~10x** |

## Implementation

Each thin wrapper agent follows this pattern:

```python
# 1. Parse the request (minimal work)
# 2. Call invoke_gemini with full context
mcp__stravinsky__invoke_gemini(
    prompt="You are the Explore specialist...\n\nTASK: {request}\n\nAVAILABLE TOOLS: ...",
    model="gemini-3-flash",
    agent_context={"agent_type": "explore", "description": "..."}
)
# 3. Return Gemini's response directly
```

## Agent Routing Summary

| Agent | Pattern | Wrapper | Work Model |
|-------|---------|---------|------------|
| explore | Thin Wrapper | haiku | gemini-3-flash |
| dewey | Thin Wrapper | haiku | gemini-3-flash |
| frontend | Thin Wrapper | haiku | gemini-3-pro-high |
| delphi | Thin Wrapper | sonnet | gpt-5.2-medium |
| code-reviewer | Native | sonnet | Claude native |
| debugger | Native | sonnet | Claude native |
| stravinsky | Orchestrator | sonnet | Claude native |

## Conclusion

The thin wrapper pattern achieves oh-my-opencode parity:
- Fast parallel execution via Task
- Cheap model routing (Haiku + Gemini)
- Multi-model support (Gemini, GPT, Claude)
- Compatible with existing Claude Code infrastructure
