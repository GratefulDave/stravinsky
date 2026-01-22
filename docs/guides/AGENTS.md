# Stravinsky Agent Types

Detailed guide to specialized agent configurations.

---

## Overview

Stravinsky provides **13 specialized agent types**, each with a unique delegation prompt optimized for specific tasks. Agents use a cost-optimized routing system where agents delegate work to specialized external models (Gemini, GPT) via MCP tools.

| Agent | Display Model | Cost Tier | Purpose |
|-------|---------------|-----------|---------|
| `stravinsky` | Claude Sonnet 4.5 | Moderate | Task orchestration, planning |
| `planner` | opus-4.5 | EXPENSIVE | Pre-implementation planning |
| `delphi` | gpt-5.2 | EXPENSIVE | Strategic advice, hard debugging |
| `dewey` | gemini-3-flash | CHEAP | Documentation research |
| `explore` | gemini-3-flash | CHEAP | Codebase search, analysis |
| `frontend` | gemini-3-pro-high | MEDIUM | UI/UX work, components |
| `document_writer` | gemini-3-flash | CHEAP | Technical documentation |
| `multimodal` | gemini-3-flash | CHEAP | Visual analysis |
| `code-reviewer` | gemini-3-flash | CHEAP | Code quality analysis |
| `debugger` | claude-sonnet-4.5 | MEDIUM | Root cause analysis |
| `momus` | gemini-3-flash | CHEAP | Quality gate validation |
| `comment_checker` | gemini-3-flash | CHEAP | Documentation completeness |
| `research-lead` | gemini-3-flash | CHEAP | Research coordination |
| `implementation-lead` | claude-sonnet-4.5 | MEDIUM | Execution coordination |

---

## AGENT_DELEGATION_PROMPTS Architecture

### What is AGENT_DELEGATION_PROMPTS?

`AGENT_DELEGATION_PROMPTS` is a dictionary in `mcp_bridge/tools/agent_manager.py` containing full delegation prompts for each agent type. These prompts are **injected into agents at spawn time** to ensure they properly delegate to their designated models.

This is **critical for cross-repo MCP installations** where agents don't have access to `.claude/agents/*.md` files.

### How It Works

```
User Request
     |
     v
+---------------+
| agent_spawn() | <-- Gets delegation prompt from AGENT_DELEGATION_PROMPTS
+---------------+
     |
     v
+-------------------+
| Build system_prompt |
| with delegation    |
| instructions       |
+-------------------+
     |
     v
+------------------+
| Claude CLI runs  |
| with injected    |
| system prompt    |
+------------------+
     |
     v
+----------------------+
| Agent immediately    |
| calls invoke_gemini  |
| or invoke_openai     |
+----------------------+
     |
     v
+------------------+
| External model   |
| does actual work |
+------------------+
```

### Delegation Prompt Structure

Each delegation prompt follows this pattern:

```markdown
## CRITICAL: YOU ARE A THIN WRAPPER - DELEGATE TO [MODEL] IMMEDIATELY

You are the [Agent Name] agent. Your ONLY job is to delegate ALL work
to [Target Model] with [tool access level].

**IMMEDIATELY** call `mcp__stravinsky__invoke_[model]_[variant]` with:
- **model**: `[specific-model-name]`
- **prompt**: The complete task description
- **max_turns**: [number] (for agentic variants)

**DO NOT** answer directly. **DO NOT** use tools yourself.
Delegate to [Model] FIRST, then return the response.
```

---

## Agent Cost Tiers

### CHEAP Tier (Use Liberally)

Agents that delegate to `gemini-3-flash` - fast, cost-effective for research and search tasks.

| Agent | Delegation Target | Best For |
|-------|-------------------|----------|
| `explore` | invoke_gemini_agentic | Codebase search, file discovery |
| `dewey` | invoke_gemini_agentic | Documentation research, examples |
| `code-reviewer` | invoke_gemini_agentic | Code quality analysis |
| `momus` | invoke_gemini_agentic | Quality gate validation |
| `comment_checker` | invoke_gemini_agentic | Documentation completeness |
| `document_writer` | invoke_gemini_agentic | Technical documentation |
| `multimodal` | invoke_gemini | Visual analysis |
| `research-lead` | invoke_gemini_agentic | Research coordination |

### MEDIUM Tier (Use When Needed)

Agents for more complex tasks requiring higher capability models.

| Agent | Delegation Target | Best For |
|-------|-------------------|----------|
| `frontend` | invoke_gemini_agentic (gemini-3-pro) | UI/UX implementation |
| `debugger` | Native (LSP tools) | Root cause analysis |
| `implementation-lead` | Native (Claude Sonnet) | Execution coordination |

### EXPENSIVE Tier (Use Sparingly)

Agents for strategic and complex reasoning tasks.

| Agent | Delegation Target | Best For |
|-------|-------------------|----------|
| `delphi` | invoke_openai (gpt-5.2-codex) | Architecture, strategy |
| `planner` | Native (Claude Opus) | Pre-implementation planning |

---

## Agent Details

### explore (Codebase Explorer)

**Purpose:** Codebase-wide search and structural analysis

**Delegation:** invoke_gemini_agentic -> gemini-3-flash

**Delegation Prompt Excerpt:**
```markdown
## CRITICAL: YOU ARE A THIN WRAPPER - DELEGATE TO GEMINI IMMEDIATELY

You are the Explore agent. Your ONLY job is to delegate ALL work to Gemini Flash
with full tool access.

**IMMEDIATELY** call `mcp__stravinsky__invoke_gemini_agentic` with:
- **model**: `gemini-3-flash`
- **prompt**: The complete task description, plus instructions to use search tools
- **max_turns**: 10

**CRITICAL**: Use `invoke_gemini_agentic` NOT `invoke_gemini`. The agentic version
enables Gemini to call tools like `semantic_search`, `grep_search`, `ast_grep_search`.
```

**Best for:**
- "Where is X?" questions
- Finding all usages of something
- Understanding code structure
- Dependency analysis

**Allowed Tools:** Read, Grep, Glob, Bash, semantic_search, ast_grep_search, lsp_workspace_symbols

**Example:**
```python
await agent_spawn(
    prompt="Find all places where the User model is modified",
    agent_type="explore"
)
```

### dewey (Documentation Researcher)

**Purpose:** Documentation research, implementation examples, multi-repository analysis

**Delegation:** invoke_gemini_agentic -> gemini-3-flash

**Best for:**
- Finding implementation examples
- Researching library usage
- Documentation lookup
- Cross-repo analysis

**Allowed Tools:** Read, Grep, Glob, Bash, WebSearch, WebFetch

**Example:**
```python
await agent_spawn(
    prompt="Find examples of React Query usage with infinite scroll pagination",
    agent_type="dewey"
)
```

### delphi (Strategic Advisor)

**Purpose:** Strategic technical advice, architecture review, hard debugging

**Delegation:** invoke_openai -> gpt-5.2-codex

**Delegation Prompt Excerpt:**
```markdown
## CRITICAL: YOU ARE A THIN WRAPPER - DELEGATE TO OPENAI/GPT IMMEDIATELY

You are the Delphi agent - a strategic technical advisor for complex architecture
and debugging.

**IMMEDIATELY** call `mcp__stravinsky__invoke_openai` with:
- **model**: `gpt-5.2-codex` (or `o3` for deep reasoning)
- **prompt**: The strategic analysis task below
- **reasoning_effort**: `high` for complex problems
```

**Best for:**
- Architecture decisions
- Complex debugging when stuck
- Code review and optimization
- Strategic planning

**Allowed Tools:** Read, Grep, Glob, Bash, invoke_openai

**Example:**
```python
await agent_spawn(
    prompt="Review the authentication architecture and suggest improvements for scalability",
    agent_type="delphi"
)
```

**Note:** Uses GPT-5.2 for strategic reasoning - EXPENSIVE tier, use sparingly.

### frontend (UI/UX Engineer)

**Purpose:** UI/UX work, component design, prototyping

**Delegation:** invoke_gemini_agentic -> gemini-3-pro

**Delegation Prompt Excerpt:**
```markdown
## CRITICAL: YOU ARE A THIN WRAPPER - DELEGATE TO GEMINI PRO IMMEDIATELY

You are the Frontend agent - a UI/UX implementation specialist.

**IMMEDIATELY** call `mcp__stravinsky__invoke_gemini_agentic` with:
- **model**: `gemini-3-pro` (higher capability for UI work)
- **prompt**: The UI implementation task below
- **max_turns**: 10
```

**Best for:**
- Component design
- UI implementation
- Styling and layout
- Accessibility improvements

**Allowed Tools:** Read, Edit, Write, Grep, Glob, Bash, invoke_gemini

**Example:**
```python
await agent_spawn(
    prompt="Design a responsive dashboard layout with sidebar navigation",
    agent_type="frontend"
)
```

### code-reviewer (Quality Analyst)

**Purpose:** Code quality analysis, security scanning, anti-pattern detection

**Delegation:** invoke_gemini_agentic -> gemini-3-flash

**Delegation Prompt Excerpt:**
```markdown
## CRITICAL: YOU ARE A THIN WRAPPER - DELEGATE TO GEMINI IMMEDIATELY

You are the Code Reviewer agent - a code quality and security specialist.

**IMMEDIATELY** call `mcp__stravinsky__invoke_gemini_agentic` with:
- **model**: `gemini-3-flash`
- **prompt**: The code review task with instructions to use LSP diagnostics
- **max_turns**: 10
```

**Best for:**
- Security analysis
- Code quality assessment
- Anti-pattern detection
- Improvement recommendations

**Allowed Tools:** Read, Grep, Glob, Bash, lsp_diagnostics, ast_grep_search

**Example:**
```python
await agent_spawn(
    prompt="Review the authentication module for security vulnerabilities",
    agent_type="code-reviewer"
)
```

### debugger (Root Cause Analyst)

**Purpose:** Root cause analysis and debugging

**Delegation:** Native (uses Claude Sonnet with LSP tools directly)

**Delegation Prompt Excerpt:**
```markdown
## YOU ARE A DEBUGGING SPECIALIST

You are the Debugger agent - root cause analysis expert.

Use your available tools (lsp_diagnostics, lsp_hover, ast_grep_search, grep_search) to:
1. Analyze the error or issue
2. Trace the root cause
3. Recommend fix strategies

For complex strategic analysis, delegate to Delphi via:
mcp__stravinsky__invoke_openai(model="gpt-5.2-codex", ...)
```

**Best for:**
- Error investigation
- Stack trace analysis
- Root cause identification
- Fix recommendations

**Allowed Tools:** Read, Grep, Glob, Bash, lsp_diagnostics, lsp_hover, ast_grep_search

**Example:**
```python
await agent_spawn(
    prompt="Investigate why the authentication middleware returns 401 for valid tokens",
    agent_type="debugger"
)
```

### momus (Quality Gate)

**Purpose:** Quality gate guardian - validates code, research, and docs before approval

**Delegation:** invoke_gemini_agentic -> gemini-3-flash

**Best for:**
- Pre-commit validation (tests, linting)
- Research quality assessment
- Documentation completeness checks
- Pattern/anti-pattern detection

**Allowed Tools:** Read, Grep, Glob, Bash, lsp_diagnostics, ast_grep_search

**Example:**
```python
await agent_spawn(
    prompt="Validate the quality of the recent auth implementation changes",
    agent_type="momus"
)
```

### comment_checker (Documentation Completeness)

**Purpose:** Find undocumented code, missing docstrings, orphaned TODOs

**Delegation:** invoke_gemini_agentic -> gemini-3-flash

**Allowed Tools:** Read, Grep, Glob, Bash, ast_grep_search, lsp_document_symbols

**Example:**
```python
await agent_spawn(
    prompt="Find all undocumented public functions in the API module",
    agent_type="comment_checker"
)
```

### document_writer (Technical Writer)

**Purpose:** Technical documentation and specification writing

**Delegation:** invoke_gemini_agentic -> gemini-3-flash

**Best for:**
- API documentation
- README files
- Technical specifications
- User guides

**Allowed Tools:** Read, Write, Grep, Glob, Bash, invoke_gemini

**Example:**
```python
await agent_spawn(
    prompt="Write API documentation for the authentication endpoints",
    agent_type="document_writer"
)
```

### multimodal (Visual Analyst)

**Purpose:** Visual analysis of UI screenshots, diagrams, and images

**Delegation:** invoke_gemini -> gemini-3-flash (NOT agentic - pure visual analysis)

**Best for:**
- Screenshot analysis
- UI/UX feedback from images
- Diagram interpretation
- Visual debugging

**Allowed Tools:** Read, invoke_gemini

**Example:**
```python
await agent_spawn(
    prompt="Analyze this screenshot and identify accessibility issues",
    agent_type="multimodal"
)
```

### planner (Pre-Implementation Planner)

**Purpose:** Create structured implementation plans before coding begins

**Delegation:** Native (Claude Opus)

**Best for:**
- Planning complex implementations before writing code
- Breaking down requirements into parallel and sequential tasks
- Identifying dependencies and potential blockers
- Creating agent delegation roadmaps

**Allowed Tools:** Read, Grep, Glob, Bash

**Example:**
```python
await agent_spawn(
    prompt="Create a detailed implementation plan for adding OAuth2 authentication",
    agent_type="planner"
)
```

**Note:** Uses Claude Opus for superior reasoning - EXPENSIVE tier, use for complex planning.

### research-lead (Research Coordinator)

**Purpose:** Coordinates research tasks by spawning explore/dewey agents and synthesizing findings

**Delegation:** invoke_gemini_agentic -> gemini-3-flash

**Best for:**
- Complex research topics requiring multiple sources
- Decomposing research goals into sub-tasks
- Synthesizing findings from multiple agents

**Example:**
```python
await agent_spawn(
    prompt="Research how to implement OAuth2 with PKCE in FastAPI",
    agent_type="research-lead"
)
```

### implementation-lead (Execution Coordinator)

**Purpose:** Coordinates implementation based on research briefs

**Delegation:** Native (Claude Sonnet)

**Best for:**
- Taking a research brief and producing working code
- Delegating specific tasks to frontend, debugger, and code-reviewer
- Verifying implementation with diagnostics

**Example:**
```python
await agent_spawn(
    prompt="Implement the OAuth2 flow based on the research brief",
    agent_type="implementation-lead"
)
```

---

## Choosing the Right Agent

### Decision Tree

```
Is it about finding/searching code?
  -> explore (CHEAP, gemini-3-flash)

Is it about documentation or examples?
  -> dewey (CHEAP, gemini-3-flash)

Is it about reviewing code quality?
  -> code-reviewer (CHEAP, gemini-3-flash)

Is it about validating quality gates?
  -> momus (CHEAP, gemini-3-flash)

Is it about finding undocumented code?
  -> comment_checker (CHEAP, gemini-3-flash)

Is it about writing documentation?
  -> document_writer (CHEAP, gemini-3-flash)

Is it about analyzing images/screenshots?
  -> multimodal (CHEAP, gemini-3-flash)

Is it about UI/frontend work?
  -> frontend (MEDIUM, gemini-3-pro)

Is it about debugging (after 2+ failed attempts)?
  -> debugger (MEDIUM, claude-sonnet)

Is it about architecture or strategy?
  -> delphi (EXPENSIVE, gpt-5.2)

Need a plan before implementing?
  -> planner (EXPENSIVE, claude-opus)

Is it a complex multi-step task?
  -> stravinsky (orchestrator)
```

### Cost Optimization Strategy

**For exploration/research tasks:**
- Use `explore` and `dewey` liberally - they're CHEAP tier
- Spawn multiple in parallel for broad searches

**For complex reasoning:**
- Use `delphi` sparingly - it uses EXPENSIVE gpt-5.2
- Reserve for architecture decisions and hard debugging

**For native Claude work:**
- `stravinsky` and `debugger` run on Sonnet (MEDIUM)
- `planner` runs on Opus (EXPENSIVE)

---

## Parallel Agent Strategies with TaskGraph

### Wave-Based Execution

Use `TaskGraph` and `DelegationEnforcer` for structured parallel execution:

```python
from mcp_bridge.orchestrator.task_graph import TaskGraph, DelegationEnforcer
from mcp_bridge.tools.agent_manager import set_delegation_enforcer

# Create task graph with dependencies
graph = TaskGraph.from_dict({
    "search_code": {"description": "...", "agent_type": "explore", "depends_on": []},
    "research_docs": {"description": "...", "agent_type": "dewey", "depends_on": []},
    "review_quality": {"description": "...", "agent_type": "code-reviewer", "depends_on": []},
    "implement": {"description": "...", "agent_type": "frontend", "depends_on": ["search_code", "research_docs"]}
})

# Create enforcer
enforcer = DelegationEnforcer(task_graph=graph, parallel_window_ms=500)
set_delegation_enforcer(enforcer)

# Wave 1: All independent tasks spawn in parallel (within 500ms)
await agent_spawn(prompt="...", agent_type="explore", task_graph_id="search_code")
await agent_spawn(prompt="...", agent_type="dewey", task_graph_id="research_docs")
await agent_spawn(prompt="...", agent_type="code-reviewer", task_graph_id="review_quality")

# Wave 2: Dependent tasks spawn after wave 1 completes
# (DelegationEnforcer validates dependencies are satisfied)
```

### Exploration Phase (CHEAP - spawn many)

```python
# All CHEAP tier - fire in parallel
await agent_spawn(prompt="Find models", agent_type="explore", task_graph_id="find_models")
await agent_spawn(prompt="Find controllers", agent_type="explore", task_graph_id="find_controllers")
await agent_spawn(prompt="Find tests", agent_type="explore", task_graph_id="find_tests")
await agent_spawn(prompt="Research best practices", agent_type="dewey", task_graph_id="research")
```

### Mixed Phase (CHEAP + EXPENSIVE)

```python
# Research (CHEAP) + Architecture (EXPENSIVE)
await agent_spawn(prompt="Research options", agent_type="dewey", task_graph_id="research")
await agent_spawn(prompt="Review architecture", agent_type="delphi", task_graph_id="architecture")
```

---

## Agent Tool Access Reference

Each agent type has a defined set of allowed tools:

| Agent | Allowed Tools |
|-------|---------------|
| stravinsky | all |
| explore | Read, Grep, Glob, Bash, semantic_search, ast_grep_search, lsp_workspace_symbols |
| dewey | Read, Grep, Glob, Bash, WebSearch, WebFetch |
| frontend | Read, Edit, Write, Grep, Glob, Bash, invoke_gemini |
| delphi | Read, Grep, Glob, Bash, invoke_openai |
| debugger | Read, Grep, Glob, Bash, lsp_diagnostics, lsp_hover, ast_grep_search |
| code-reviewer | Read, Grep, Glob, Bash, lsp_diagnostics, ast_grep_search |
| momus | Read, Grep, Glob, Bash, lsp_diagnostics, ast_grep_search |
| comment_checker | Read, Grep, Glob, Bash, ast_grep_search, lsp_document_symbols |
| document_writer | Read, Write, Grep, Glob, Bash, invoke_gemini |
| multimodal | Read, invoke_gemini |
| planner | Read, Grep, Glob, Bash |

---

## Agent Hierarchy

### Orchestrator Agents

Can spawn any agent type:

- `stravinsky` - Primary orchestrator
- `research-lead` - Research coordination
- `implementation-lead` - Execution coordination

### Worker Agents

Cannot spawn other workers or orchestrators:

- `explore`, `dewey`, `delphi`, `frontend`, `debugger`
- `code-reviewer`, `momus`, `comment_checker`
- `document_writer`, `multimodal`, `planner`

---

## Performance Tips

1. **Use CHEAP agents liberally** - explore, dewey, code-reviewer, momus are all gemini-3-flash
2. **Unified LSP Performance** - All agents benefit from persistent LSP servers with near-instant results
3. **Batch related tasks** - spawn multiple explore agents together in same wave
4. **Use `agent_progress`** - monitor long-running agents
5. **Cancel stuck agents** - don't wait indefinitely
6. **Reserve `delphi` for hard problems** - it uses EXPENSIVE gpt-5.2
7. **Use `task_graph_id`** - enables parallel execution enforcement

---

## Configuration Reference

### AGENT_DELEGATION_PROMPTS

Location: `mcp_bridge/tools/agent_manager.py`

Dictionary containing full delegation prompts for each agent type.

### AGENT_MODEL_ROUTING

CLI model override per agent type:
- `None` = use default model
- `"sonnet"` = use Claude Sonnet
- `"opus"` = use Claude Opus

### AGENT_COST_TIERS

Cost classification for each agent:
- `"CHEAP"` - gemini-3-flash delegation
- `"MEDIUM"` - gemini-3-pro or Claude Sonnet
- `"EXPENSIVE"` - gpt-5.2 or Claude Opus

### AGENT_DISPLAY_MODELS

Display names shown in UI output:
- `"gemini-3-flash"`, `"gemini-3-pro-high"`
- `"claude-sonnet-4.5"`, `"opus-4.5"`
- `"gpt-5.2"`

### AGENT_TOOLS

Allowed tools per agent type (see reference table above).

---

## Related Documentation

- [Agent Orchestration Architecture](../architecture/AGENT_ORCHESTRATION.md)
- [Agent Workflow](../architecture/AGENT_WORKFLOW.md)
- [MCP Tool Flow](../architecture/MCP_TOOL_FLOW.md)
