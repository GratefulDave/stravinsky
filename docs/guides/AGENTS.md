# Stravinsky Agent Types

Detailed guide to specialized agent configurations.

---

## Overview

Stravinsky provides **13 specialized agent types**, with **12 having full delegation prompts** in `AGENT_DELEGATION_PROMPTS`. Agents use a cost-optimized routing system where agents delegate work to specialized external models (Gemini, GPT) via MCP tools.

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

| Agent | Delegation Target | Full Prompt | Best For |
|-------|-------------------|-------------|----------|
| `explore` | invoke_gemini_agentic | Yes | Codebase search, file discovery |
| `dewey` | invoke_gemini_agentic | Yes | Documentation research, examples |
| `code-reviewer` | invoke_gemini_agentic | Yes | Code quality analysis |
| `momus` | invoke_gemini_agentic | Yes | Quality gate validation |
| `comment_checker` | invoke_gemini_agentic | Yes | Documentation completeness |
| `document_writer` | invoke_gemini_agentic | Yes | Technical documentation |
| `multimodal` | invoke_gemini | Yes | Visual analysis |
| `research-lead` | invoke_gemini_agentic | Yes | Research coordination, parallel agent spawning |

### MEDIUM Tier (Use When Needed)

Agents for more complex tasks requiring higher capability models.

| Agent | Delegation Target | Full Prompt | Best For |
|-------|-------------------|-------------|----------|
| `frontend` | invoke_gemini_agentic (gemini-3-pro) | Yes | UI/UX implementation |
| `debugger` | Native (LSP tools) | Yes | Root cause analysis |
| `implementation-lead` | invoke_gemini_agentic | Yes | Execution coordination, agent workflow |

### EXPENSIVE Tier (Use Sparingly)

Agents for strategic and complex reasoning tasks.

| Agent | Delegation Target | Full Prompt | Best For |
|-------|-------------------|-------------|----------|
| `delphi` | invoke_openai (gpt-5.2-codex) | Yes | Architecture, strategy |
| `planner` | Native (Claude Opus) | Yes | Pre-implementation planning |

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

**Purpose:** Coordinates research tasks by spawning explore/dewey agents in parallel and synthesizing findings

**Delegation:** invoke_gemini_agentic -> gemini-3-flash

**Full Delegation Prompt:** Yes - includes parallel spawn instructions for explore/dewey agents

**Delegation Prompt Excerpt:**
```markdown
## CRITICAL: YOU ARE A THIN WRAPPER - DELEGATE TO GEMINI IMMEDIATELY

You are the Research Lead agent. Your ONLY job is to delegate ALL work to Gemini Flash
with full tool access to coordinate research across explore and dewey agents.

**IMMEDIATELY** call `mcp__stravinsky__invoke_gemini_agentic` with:
- **model**: `gemini-3-flash`
- **prompt**: The research task with instructions to spawn parallel explore/dewey agents
- **max_turns**: 15

**CRITICAL**: Use `invoke_gemini_agentic` NOT `invoke_gemini`. The agentic version
enables Gemini to spawn parallel agents via agent_spawn.

**PARALLEL SPAWN PATTERN**: For complex research:
1. Spawn multiple explore agents for different code areas
2. Spawn dewey agents for documentation/examples
3. Synthesize findings into a research brief
```

**Best for:**
- Complex research topics requiring multiple sources
- Decomposing research goals into parallel sub-tasks
- Spawning explore/dewey agents and synthesizing findings
- Creating research briefs for implementation-lead

**Allowed Tools:** Read, Grep, Glob, Bash, agent_spawn, agent_output

**Example:**
```python
await agent_spawn(
    prompt="Research how to implement OAuth2 with PKCE in FastAPI",
    agent_type="research-lead"
)
```

### implementation-lead (Execution Coordinator)

**Purpose:** Coordinates implementation based on research briefs by delegating to frontend, debugger, and code-reviewer agents

**Delegation:** invoke_gemini_agentic -> gemini-3-flash

**Full Delegation Prompt:** Yes - includes coordination workflow for frontend/debugger/code-reviewer

**Delegation Prompt Excerpt:**
```markdown
## CRITICAL: YOU ARE A THIN WRAPPER - DELEGATE TO GEMINI IMMEDIATELY

You are the Implementation Lead agent. Your ONLY job is to delegate ALL work to Gemini Flash
with full tool access to coordinate implementation across specialized agents.

**IMMEDIATELY** call `mcp__stravinsky__invoke_gemini_agentic` with:
- **model**: `gemini-3-flash`
- **prompt**: The implementation task with instructions to coordinate agents
- **max_turns**: 20

**CRITICAL**: Use `invoke_gemini_agentic` NOT `invoke_gemini`. The agentic version
enables Gemini to spawn and coordinate agents.

**COORDINATION WORKFLOW**:
1. Parse the research brief or implementation requirements
2. Spawn frontend agent for UI/component work
3. Spawn debugger agent if errors arise during implementation
4. Spawn code-reviewer agent to validate quality before completion
5. Use lsp_diagnostics to verify implementation has no errors
```

**Best for:**
- Taking a research brief and producing working code
- Coordinating frontend, debugger, and code-reviewer agents
- Managing implementation workflow with quality gates
- Verifying implementation with diagnostics

**Allowed Tools:** Read, Edit, Write, Grep, Glob, Bash, agent_spawn, agent_output, lsp_diagnostics

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
| research-lead | Read, Grep, Glob, Bash, agent_spawn, agent_output |
| implementation-lead | Read, Edit, Write, Grep, Glob, Bash, agent_spawn, agent_output, lsp_diagnostics |

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

**Coverage:** 12 of 13 agent types have full delegation prompts:

| Agent | Has Delegation Prompt | Notes |
|-------|----------------------|-------|
| explore | Yes | Parallel search with gemini-3-flash |
| dewey | Yes | Documentation research with gemini-3-flash |
| delphi | Yes | Strategic advice with gpt-5.2-codex |
| frontend | Yes | UI/UX with gemini-3-pro |
| code-reviewer | Yes | Quality analysis with gemini-3-flash |
| debugger | Yes | Root cause analysis with LSP tools |
| momus | Yes | Quality gate validation with gemini-3-flash |
| comment_checker | Yes | Documentation completeness with gemini-3-flash |
| document_writer | Yes | Technical writing with gemini-3-flash |
| multimodal | Yes | Visual analysis with gemini-3-flash |
| planner | Yes | Pre-implementation planning (native Opus) |
| research-lead | Yes | Parallel spawn for explore/dewey with gemini-3-flash |
| implementation-lead | Yes | Coordination workflow for frontend/debugger/code-reviewer with gemini-3-flash |
| stravinsky | No | Primary orchestrator uses native Claude |

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
