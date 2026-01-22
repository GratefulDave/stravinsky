# Model Routing and Delegation Architecture

Stravinsky features a sophisticated **Tier-Aware Multi-Provider Routing System** designed for high availability, cost-efficiency, and resilience.

---

## Agent Model Configuration

Model routing is defined in `mcp_bridge/tools/agent_manager.py`. Each agent type has a designated display model and cost tier.

### AGENT_DISPLAY_MODELS

| Agent Type | Display Model | Purpose |
|------------|---------------|---------|
| `explore` | gemini-3-flash | Codebase search, file discovery |
| `dewey` | gemini-3-flash | Documentation research, web search |
| `document_writer` | gemini-3-flash | Technical documentation generation |
| `multimodal` | gemini-3-flash | Visual analysis (screenshots, diagrams) |
| `research-lead` | gemini-3-flash | Research coordination |
| `momus` | gemini-3-flash | Quality gate validation |
| `comment_checker` | gemini-3-flash | Documentation completeness checking |
| `code-reviewer` | gemini-3-flash | Code quality and security review |
| `implementation-lead` | claude-sonnet-4.5 | Implementation coordination |
| `debugger` | claude-sonnet-4.5 | Root cause analysis |
| `frontend` | gemini-3-pro-high | UI/UX implementation |
| `delphi` | gpt-5.2 | Strategic technical advice |
| `planner` | opus-4.5 | Complex planning tasks |
| `_default` | sonnet-4.5 | Fallback for unknown agent types |

### AGENT_COST_TIERS

| Tier | Agents | Indicator |
|------|--------|-----------|
| **CHEAP** | explore, dewey, document_writer, multimodal, research-lead, momus, comment_checker, code-reviewer | Green |
| **MEDIUM** | implementation-lead, debugger, frontend | Blue |
| **EXPENSIVE** | delphi, planner | Purple |

---

## Model Tiers by Provider

Models are classified into three tiers based on capability, cost, and use case:

| Tier | Claude (Anthropic) | OpenAI (ChatGPT) | Gemini (Google) | Use Case |
|------|--------------------|------------------|-----------------|----------|
| **HIGH** | Claude 4.5 Opus (Thinking) | GPT 5.2 | Gemini 3 Pro | Architecture, strategic decisions, complex debugging |
| **PREMIUM** | Claude 4.5 Opus | GPT 5.2 Codex | Gemini 3 Pro | Code generation, complex implementation |
| **STANDARD** | Claude 4.5 Sonnet | GPT 5.2 | Gemini 3 Flash | Documentation, code search, simple tasks |

### HIGH Tier: Strategic Reasoning

The **HIGH tier** is reserved for tasks requiring deep strategic thinking:
- Architecture review and design decisions
- Complex debugging after 2+ failed attempts
- Security vulnerability analysis
- Performance optimization strategies
- Multi-system tradeoff evaluation

| Provider | Model | Configuration | Strengths |
|----------|-------|---------------|-----------|
| OpenAI | GPT 5.2 | Default | Deep reasoning, strategic analysis |
| Claude | 4.5 Opus | `thinking_budget > 0` | Extended thinking, architectural decisions |
| Gemini | 3 Pro | Default | Multi-modal analysis, UI/UX evaluation |

### Claude 4.5 Opus "Thinking" Mode

The HIGH-tier Claude 4.5 Opus model supports an extended "Thinking" mode (enabled via `thinking_budget` > 0), allowing for deep reasoning on complex architectural or logic problems.

---

## Delegation Flow

### Agent Spawn Delegation Chain

```
agent_spawn(prompt, agent_type, task_graph_id)
    |
    v
[DelegationEnforcer validates parallel execution]
    |
    v
[System prompt includes AGENT_DELEGATION_PROMPTS[agent_type]]
    |
    v
[Claude CLI subprocess spawned with model from AGENT_MODEL_ROUTING]
    |
    v
[Agent delegates to target model via invoke_gemini_agentic or invoke_openai]
```

### Agent Delegation Prompts

Each agent type has a delegation prompt that instructs it to delegate to its target model. These prompts are injected into agents spawned via MCP, ensuring proper delegation even in cross-repository installations.

**Key delegation patterns:**

| Agent Type | Delegation Target | Tool Used |
|------------|-------------------|-----------|
| explore | Gemini Flash | `invoke_gemini_agentic` with `max_turns=10` |
| dewey | Gemini Flash | `invoke_gemini_agentic` with `max_turns=10` |
| research-lead | Gemini Flash | `invoke_gemini_agentic` with `max_turns=10` |
| implementation-lead | Claude Sonnet 4.5 | Direct execution (no delegation, uses Claude CLI directly) |
| frontend | Gemini Pro | `invoke_gemini_agentic` with `max_turns=10` |
| delphi | GPT 5.2 Codex | `invoke_openai` with `reasoning_effort="high"` |
| code-reviewer | Gemini Flash | `invoke_gemini_agentic` with `max_turns=10` |
| debugger | Claude Sonnet 4.5 | Uses LSP/AST tools directly, delegates complex analysis to delphi |
| momus | Gemini Flash | `invoke_gemini_agentic` with `max_turns=10` |
| document_writer | Gemini Flash | `invoke_gemini_agentic` with `max_turns=10` |
| multimodal | Gemini Flash | `invoke_gemini` (non-agentic for pure visual analysis) |
| comment_checker | Gemini Flash | `invoke_gemini_agentic` with `max_turns=10` |

**Orchestrator vs Worker Delegation:**
- **research-lead**: Coordinates research tasks, delegates to Gemini Flash for cost efficiency (CHEAP tier)
- **implementation-lead**: Coordinates implementation tasks, uses Claude Sonnet 4.5 directly for code quality (MEDIUM tier). Fixed in v0.4.56 to use correct model routing (was incorrectly using Haiku before this version).

**Critical distinction:**
- `invoke_gemini_agentic`: Enables Gemini to call tools (semantic_search, grep_search, ast_grep_search, etc.)
- `invoke_gemini`: Simple completion without tool access

---

## OAuth-First Fallback Architecture

Stravinsky prioritizes secure OAuth authentication while maintaining robust fallback mechanisms to ensure task continuity even during rate limits or provider outages.

### Fallback Priority Matrix

When a model call fails (e.g., due to a 429 Rate Limit or 5xx error), Stravinsky follows this deterministic fallback chain:

| Priority | Strategy | Description |
|----------|----------|-------------|
| **1** | **Cross-Provider OAuth** | Attempts the same tier model from a different provider using OAuth. |
| **2** | **Lower-Tier OAuth** | Falls back to a STANDARD tier model from any available provider using OAuth. |
| **3** | **API Key Fallback** | As a last resort, attempts the original model tier using a configured API key. |

**Example Chain (Starting with GPT 5.2 Codex OAuth):**
1. Gemini 3 Pro (OAuth)
2. Claude 4.5 Opus (OAuth)
3. GPT 5.2 (OAuth)
4. Gemini 3 Flash (OAuth)
5. GPT 5.2 Codex (API Key)

---

## Task-Based Routing

You can define specific models for different types of work in your project to balance cost and capability.

### Configuration: `.stravinsky/routing.json`

Project-local routing rules are stored in `.stravinsky/routing.json`. This configuration allows you to override default models for specific tasks.

```json
{
  "routing": {
    "task_routing": {
      "architecture": {
        "provider": "openai",
        "model": "gpt-5.2",
        "tier": "high",
        "description": "Architecture review, strategic decisions, complex tradeoffs"
      },
      "security_review": {
        "provider": "openai",
        "model": "gpt-5.2",
        "tier": "high",
        "description": "Security vulnerability analysis and threat modeling"
      },
      "code_generation": {
        "provider": "openai",
        "model": "gpt-5.2-codex",
        "tier": "premium",
        "description": "Complex code generation tasks"
      },
      "debugging": {
        "provider": "openai",
        "model": "gpt-5.2-codex",
        "tier": "premium",
        "description": "Code analysis and debugging"
      },
      "documentation": {
        "provider": "gemini",
        "model": "gemini-3-flash",
        "tier": "standard",
        "description": "Documentation writing"
      },
      "code_search": {
        "provider": "gemini",
        "model": "gemini-3-flash",
        "tier": "standard",
        "description": "Finding code patterns"
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

---

## Routing CLI Commands

Manage provider health and routing configuration via the CLI:

- **View Status**: `stravinsky-auth routing status`
  Displays health, auth readiness, and request statistics for all providers.
- **Initialize Config**: `stravinsky-auth routing init`
  Creates a default `.stravinsky/routing.json` in the current directory.
- **Reset Cooldowns**: `stravinsky-auth routing reset [provider]`
  Manually clears rate-limit cooldowns for a specific provider (or all providers if omitted).

---

## Thin Wrapper Pattern

To maintain low latency and cost, Stravinsky uses "Thin Wrapper" agents (Claude Haiku/Sonnet) that immediately delegate work to the routed external models via MCP tools. This achieves significant cost savings compared to running all agents on expensive models.

### How It Works

1. **Agent receives task** via `agent_spawn`
2. **Delegation prompt injected** - tells agent to delegate to target model
3. **Agent calls MCP tool** - `invoke_gemini_agentic` or `invoke_openai`
4. **Target model executes** with full tool access
5. **Result returned** through the chain

### Example Delegation Prompt (explore agent)

```
## CRITICAL: YOU ARE A THIN WRAPPER - DELEGATE TO GEMINI IMMEDIATELY

You are the Explore agent. Your ONLY job is to delegate ALL work to Gemini Flash with full tool access.

**IMMEDIATELY** call `mcp__stravinsky__invoke_gemini_agentic` with:
- **model**: `gemini-3-flash`
- **prompt**: The complete task description below, plus instructions to use search tools
- **max_turns**: 10 (allow multi-step search workflows)

**CRITICAL**: Use `invoke_gemini_agentic` NOT `invoke_gemini`. The agentic version enables Gemini to call tools like `semantic_search`, `grep_search`, `ast_grep_search` - the plain version cannot.
```

---

## Lead Agent Routing

The 7-Phase Orchestrator uses two specialized lead agents for coordinating research and implementation phases. These leads have distinct model routing configurations optimized for their roles.

### research-lead

| Property | Value |
|----------|-------|
| **Display Model** | gemini-3-flash |
| **Cost Tier** | CHEAP (Green) |
| **Delegation** | `invoke_gemini_agentic` with `max_turns=10` |
| **Configuration** | `AGENT_MODEL_ROUTING`, `AGENT_COST_TIERS`, `AGENT_DISPLAY_MODELS`, `AGENT_DELEGATION_PROMPTS` |

**Purpose**: Coordinates research phases by spawning and managing explore/dewey agents. Uses Gemini Flash for cost efficiency since research coordination involves primarily task distribution and result aggregation.

**Delegation Pattern**: Delegates to Gemini Flash via `invoke_gemini_agentic`, enabling full tool access for coordinating search operations across multiple worker agents.

### implementation-lead

| Property | Value |
|----------|-------|
| **Display Model** | claude-sonnet-4.5 |
| **Cost Tier** | MEDIUM (Blue) |
| **Delegation** | Direct execution (no delegation wrapper) |
| **Configuration** | `AGENT_MODEL_ROUTING`, `AGENT_COST_TIERS`, `AGENT_DISPLAY_MODELS`, `AGENT_DELEGATION_PROMPTS` |

**Purpose**: Coordinates implementation phases by executing code changes and spawning specialist agents (debugger, code-reviewer). Uses Claude Sonnet 4.5 for higher code quality and reasoning capability.

**Delegation Pattern**: Executes directly via Claude CLI without delegating to another model. This ensures high-quality code generation and implementation coordination.

**Version Note**: Prior to v0.4.56, implementation-lead was incorrectly using Haiku due to missing routing configuration. This was fixed to properly route to Claude Sonnet 4.5.

---

## Agent Hierarchy

### Orchestrator Agents

Orchestrators coordinate work and can spawn any agent type:
- `stravinsky`
- `research-lead`
- `implementation-lead`

### Worker Agents

Workers execute specific tasks and cannot spawn other agents:
- `explore` - Codebase search specialist
- `dewey` - Documentation researcher
- `delphi` - Strategic advisor
- `frontend` - UI/UX specialist
- `debugger` - Root cause analyst
- `code-reviewer` - Quality reviewer
- `momus` - Quality gate validator
- `comment_checker` - Documentation checker
- `document_writer` - Technical writer
- `multimodal` - Visual analyst
- `planner` - Planning specialist

### Hierarchy Rules

1. **Orchestrators can spawn any agent**
2. **Workers cannot spawn orchestrators**
3. **Workers cannot spawn other workers**

This prevents runaway agent chains and ensures clear execution paths.
