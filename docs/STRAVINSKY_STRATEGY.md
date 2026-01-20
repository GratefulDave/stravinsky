# Stravinsky Strategy Document

## Overview

Stravinsky is a **multi-model AI orchestration system** that bridges Claude Code with external AI providers (Gemini, OpenAI) through MCP (Model Context Protocol). This document defines the unified strategy for agent delegation, model routing, and skill orchestration.

---

## Model Tier Architecture

Stravinsky uses a **3-tier model routing system** to balance capability and cost:

| Tier | Purpose | Models | Cost |
|------|---------|--------|------|
| **HIGH** | Strategic reasoning, architecture review, complex debugging | GPT-5.2, Claude 4.5 Opus (Thinking), Gemini 3 Pro | $$$ |
| **PREMIUM** | Code generation, implementation, standard debugging | GPT-5.2 Codex, Claude 4.5 Opus, Gemini 3 Pro | $$ |
| **STANDARD** | Documentation, code search, simple tasks | GPT-5.2, Claude 4.5 Sonnet, Gemini 3 Flash Preview | $ |

### HIGH Tier Use Cases
- Architecture review and design decisions
- Complex debugging after 2+ failed attempts
- Security vulnerability analysis
- Performance optimization strategies
- Multi-system tradeoff evaluation

### PREMIUM Tier Use Cases
- Complex code generation
- Refactoring tasks
- Standard debugging
- Test generation

### STANDARD Tier Use Cases
- Documentation writing
- Code search and exploration
- Simple Q&A
- File operations

---

## Native Subagent Architecture

Stravinsky delegates specialized work to **9 native subagents**:

| Agent | Model Tier | Purpose | When to Use |
|-------|------------|---------|-------------|
| `stravinsky` | PREMIUM | Task orchestration, parallel execution | Auto-delegated for complex tasks |
| `research-lead` | STANDARD | Research coordination | Multi-source research needs |
| `implementation-lead` | STANDARD | Implementation coordination | Multi-file implementations |
| `explore` | STANDARD | Codebase search | "Where is X?", pattern finding |
| `dewey` | STANDARD | Documentation research | External docs, OSS examples |
| `code-reviewer` | PREMIUM | Quality analysis | Pre-commit review, security scan |
| `debugger` | PREMIUM | Root cause analysis | After 2+ failed fix attempts |
| `frontend` | HIGH | UI/UX implementation | Visual changes, component design |
| `delphi` | HIGH | Strategic advisor | Architecture, complex decisions |

### Delegation Rules

1. **Frontend visual changes** -> Always delegate to `frontend` agent
2. **External library questions** -> Fire `dewey` background task
3. **Codebase exploration** -> Fire `explore` background task
4. **Architecture decisions** -> Consult `delphi` first
5. **Complex debugging** -> Escalate to `debugger` after 2 failures

---

## Skill/Slash Command Architecture

Skills are discoverable slash commands stored in `.claude/commands/`:

### Core Skills

| Skill | Trigger | Purpose | Model Tier |
|-------|---------|---------|------------|
| `/strav` | Complex tasks | Task orchestration with parallel execution | PREMIUM |
| `/delphi` | Architecture | Strategic technical advisor | HIGH |
| `/dewey` | Research | Documentation and OSS research | STANDARD |
| `/arch-review` | Architecture | Comprehensive architecture review | HIGH |
| `/security-scan` | Security | Security vulnerability scanning | HIGH |
| `/perf-opt` | Performance | Performance optimization analysis | HIGH |
| `/doc-gen` | Documentation | Automated documentation generation | STANDARD |
| `/verify` | Validation | Post-implementation verification | PREMIUM |
| `/publish` | Release | PyPI publication workflow | STANDARD |

### Skill Discovery

Skills are discovered from:
- Project-local: `.claude/commands/**/*.md` (recursive)
- User-global: `~/.claude/commands/**/*.md` (recursive)

---

## Routing Configuration

### Default Routing (`.stravinsky/routing.json`)

```json
{
  "routing": {
    "task_routing": {
      "architecture": {
        "provider": "openai",
        "model": "gpt-5.2",
        "tier": "high"
      },
      "security_review": {
        "provider": "openai",
        "model": "gpt-5.2",
        "tier": "high"
      },
      "code_generation": {
        "provider": "openai",
        "model": "gpt-5.2-codex",
        "tier": "premium"
      },
      "debugging": {
        "provider": "openai",
        "model": "gpt-5.2-codex",
        "tier": "premium"
      },
      "documentation": {
        "provider": "gemini",
        "model": "gemini-3-flash-preview",
        "tier": "standard"
      },
      "code_search": {
        "provider": "gemini",
        "model": "gemini-3-flash-preview",
        "tier": "standard"
      }
    },
    "fallback": {
      "enabled": true,
      "chain": ["claude", "openai", "gemini"],
      "cooldown_seconds": 300
    }
  }
}
```

### Fallback Priority

1. **Cross-Provider OAuth** - Same tier, different provider
2. **Lower-Tier OAuth** - Standard tier fallback
3. **API Key Fallback** - Last resort using configured API key

---

## Parallel Execution Strategy

### When to Parallelize

| Scenario | Action |
|----------|--------|
| 2+ independent search queries | Fire multiple `explore` agents |
| Research + implementation | Fire `dewey` + `explore` in parallel |
| Multi-file changes | Spawn parallel implementation agents |
| Multi-provider research | Fire `librarian` agents for each source |

### Execution Pattern

```python
# Spawn all agents simultaneously
task_id_1 = agent_spawn(prompt="Search for auth patterns", agent_type="explore")
task_id_2 = agent_spawn(prompt="Find JWT best practices", agent_type="dewey")
task_id_3 = agent_spawn(prompt="Analyze security implications", agent_type="delphi")

# Collect results (blocks until complete)
result_1 = agent_output(task_id_1, block=True)
result_2 = agent_output(task_id_2, block=True)
result_3 = agent_output(task_id_3, block=True)

# Synthesize findings
# [analysis here]
```

---

## Cost Optimization

### Agent Cost Matrix

| Agent Type | Cost | Async? | When to Use |
|------------|------|--------|-------------|
| `explore` | FREE | Yes | Always for codebase search |
| `dewey` | CHEAP | Yes | Documentation, external research |
| `code-reviewer` | MEDIUM | No | Pre-commit, PR review |
| `debugger` | MEDIUM | No | After 2+ failures |
| `frontend` | EXPENSIVE | No | UI/UX only |
| `delphi` | EXPENSIVE | No | Architecture, strategic |

### Cost Rules

1. **Always async** for explore/dewey - they're cheap/free
2. **Only sync** for expensive agents when results are critical
3. **Batch operations** where possible to reduce API calls
4. **Use STANDARD tier** for exploration, save HIGH for decisions

---

## Hook System

Stravinsky uses hooks for delegation enforcement:

### PreToolUse Hooks
- `stravinsky_mode.py` - Delegation enforcer (blocks direct tools in stravinsky mode)
- `notification_hook.py` - Agent spawn notifications

### PostToolUse Hooks
- `truncator.py` - Output truncation
- `tool_messaging.py` - User messaging
- `edit_recovery.py` - Edit backup
- `todo_delegation.py` - Parallel reminder
- `parallel_execution.py` - Parallel enforcement
- `subagent_stop.py` - Agent completion handling

### UserPromptSubmit Hooks
- `context.py` - Context injection
- `todo_continuation.py` - Todo continuation

---

## Best Practices

### Do's
- Always create todos for multi-step tasks
- Fire explore/dewey agents in background
- Consult delphi for architecture decisions
- Use appropriate model tier for task complexity
- Mark todos complete immediately after finishing

### Don'ts
- Don't suppress type errors (`as any`, `@ts-ignore`)
- Don't commit without explicit request
- Don't speculate about unread code
- Don't leave code in broken state
- Don't skip todos on non-trivial tasks

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-20 | Initial strategy document |

