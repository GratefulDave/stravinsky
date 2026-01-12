# Integration Wiring Rules

## Lesson Learned: Tool-Agent Integration (2026-01-11)

**Problem**: Sub-agents fail silently when tools are "wired in" but not actually usable.

**Root Cause**: Adding a tool to an agent's tool list doesn't guarantee the agent can USE it.

## Integration Checklist (MANDATORY)

When integrating Tool X into Agent Y:

### 1. Verify Invocation Method

| Agent Type | Invocation Method | Tool Access |
|------------|-------------------|-------------|
| `invoke_gemini` | Simple completion | NO tool calling |
| `invoke_gemini_agentic` | Agentic loop | YES - full tool access |
| `invoke_openai` | Direct call | Depends on model |

**CRITICAL**: If agent needs to call tools, it MUST use the `_agentic` variant.

```python
# WRONG: Agent can't use tools
invoke_gemini(prompt="Find auth code", model="gemini-3-flash")

# RIGHT: Agent can call semantic_search, grep, etc.
invoke_gemini_agentic(
    prompt="Find auth code using semantic_search",
    model="gemini-3-flash",
    max_iterations=5
)
```

### 2. Verify Prerequisites

Some tools have prerequisites that must be met BEFORE use:

| Tool | Prerequisite | Check |
|------|--------------|-------|
| `semantic_search` | Index must exist | Run `semantic_index()` first |
| `lsp_*` | LSP server must be running | Check `lsp_servers()` |
| `invoke_*` | Auth must be configured | Run `stravinsky-auth status` |

**Add explicit checks**: Tools should fail EARLY with clear error messages if prerequisites are not met.

### 3. Verify Parent Agent Guidance

Parent agents (orchestrators) must guide sub-agents to USE the tool:

| Level | Responsibility |
|-------|----------------|
| **Orchestrator** (stravinsky) | Tell sub-agents WHEN to use which tools |
| **Coordinator** (research-lead) | Tell explore/dewey HOW to use tools for query types |
| **Worker** (explore) | Actually CALL the tools |

**If a tool is available but never used**, check the guidance chain.

### 4. Verification Pattern

After wiring a tool, verify the FULL chain:

```
Step 1: Tool is in agent's tool list      ✓
Step 2: Agent uses correct invocation     ✓  
Step 3: Prerequisites are met/checked     ✓
Step 4: Parent agents guide usage         ✓
Step 5: End-to-end test works             ✓
```

## Example: semantic_search Integration (Fixed 2026-01-11)

**Original Problem**: explore agent had semantic_search in tool list but never used it.

**Root Causes Found**:
1. explore.md called `invoke_gemini` (no tool access) instead of `invoke_gemini_agentic`
2. semantic_search returned empty results when no index existed (silent failure)
3. research-lead.md didn't tell explore agents WHEN to use semantic_search

**Fixes Applied**:
1. Changed explore.md to use `invoke_gemini_agentic` with `max_iterations: 5`
2. Added index existence check in semantic_search.py with clear error message
3. Added "Pattern 3: Semantic/Conceptual Search" to research-lead.md

## Rule

**When adding a tool to an agent, verify the FULL integration chain.**

Silent failures waste hours of debugging. Fail early, fail loudly.
