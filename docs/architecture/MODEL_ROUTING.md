# Model Routing & Fallback Architecture

Stravinsky features a sophisticated **Tier-Aware Multi-Provider Routing System** designed for high availability, cost-efficiency, and resilience.

## Model Tiers

Models are classified into three tiers based on capability, cost, and use case:

| Tier | Claude (Anthropic) | OpenAI (ChatGPT) | Gemini (Google) | Use Case |
|------|--------------------|------------------|-----------------|----------|
| **HIGH** | Claude 4.5 Opus (Thinking) | GPT 5.2 | Gemini 3 Pro | Architecture, strategic decisions, complex debugging |
| **PREMIUM** | Claude 4.5 Opus | GPT 5.2 Codex | Gemini 3 Pro | Code generation, complex implementation |
| **STANDARD**| Claude 4.5 Sonnet | GPT 5.2 | Gemini 3 Flash Preview | Documentation, code search, simple tasks |

### HIGH Tier: Strategic Reasoning

The **HIGH tier** is reserved for tasks requiring deep strategic thinking:
- **Architecture review and design decisions**
- **Complex debugging after 2+ failed attempts**
- **Security vulnerability analysis**
- **Performance optimization strategies**
- **Multi-system tradeoff evaluation**

| Provider | Model | Configuration | Strengths |
|----------|-------|---------------|-----------|
| OpenAI | GPT 5.2 | Default | Deep reasoning, strategic analysis |
| Claude | 4.5 Opus | `thinking_budget > 0` | Extended thinking, architectural decisions |
| Gemini | 3 Pro | Default | Multi-modal analysis, UI/UX evaluation |

### Claude 4.5 Opus "Thinking" Mode
The HIGH-tier Claude 4.5 Opus model supports an extended "Thinking" mode (enabled via `thinking_budget` > 0), allowing for deep reasoning on complex architectural or logic problems.

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
1. → Gemini 3 Pro (OAuth)
2. → Claude 4.5 Opus (OAuth)
3. → GPT 5.2 (OAuth)
4. → Gemini 3 Flash Preview (OAuth)
5. → GPT 5.2 Codex (API Key)

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
        "model": "gemini-3-flash-preview",
        "tier": "standard",
        "description": "Documentation writing"
      },
      "code_search": {
        "provider": "gemini",
        "model": "gemini-3-flash-preview",
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

## Thin Wrapper Pattern (Internal)

To maintain low latency and cost, Stravinsky uses "Thin Wrapper" agents (Claude Haiku) that immediately delegate work to the routed external models via MCP tools. This achieves ~10x cost savings compared to running all agents on Claude Sonnet.
