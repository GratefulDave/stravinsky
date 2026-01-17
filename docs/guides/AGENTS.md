d# Stravinsky Agent Types

Detailed guide to specialized agent configurations.

---

## Overview

Stravinsky provides 7 specialized agent types, each with a unique system prompt optimized for specific tasks.

**Thin Wrapper Architecture:** Agents now use a cost-optimized routing system where cheaper models (Haiku) delegate work to specialized external models (Gemini, GPT) via MCP tools, while expensive native Claude work runs directly on Sonnet.

| Agent | Specialty | Purpose |
|-------|-----------|---------|
| `stravinsky` | Orchestration | Task orchestration, planning |
| `planner` | Planning | Pre-implementation planning (Opus) |
| `delphi` | Strategy | Strategic advice, hard debugging |
| `dewey` | Research | Documentation research |
| `explore` | Search | Codebase search, analysis |
| `frontend` | UI/UX | UI/UX work, components |
| `document_writer` | Writing | Technical documentation |
| `multimodal` | Vision | Visual analysis |

---

## Thin Wrapper Architecture

### What is a Thin Wrapper?

A thin wrapper agent uses a cheap model (Haiku) to:
1. Parse the incoming request
2. Immediately delegate ALL work to `invoke_gemini` or `invoke_openai`
3. Return the external model's results

**No direct tool usage** - the wrapper simply routes work to the appropriate model.

### Why Thin Wrappers?

- **Cost savings:** ~10x cheaper than running Sonnet for exploration/research
- **Specialized models:** Gemini excels at code search, GPT excels at strategic reasoning
- **Parallel efficiency:** Cheap wrappers can spawn many simultaneous external calls

### Model Routing Table

| Agent | Wrapper Model | Actual Work Model | Cost Tier |
|-------|---------------|-------------------|-----------|
| `explore` | Haiku | gemini-3-flash | Free |
| `dewey` | Haiku | gemini-3-flash | Cheap |
| `document_writer` | Haiku | gemini-3-flash | Cheap |
| `multimodal` | Haiku | gemini-3-flash | Cheap |
| `research-lead` | Haiku | gemini-3-flash | Cheap |
| `code-reviewer` | Sonnet | Claude native | Cheap |
| `debugger` | Sonnet | Claude native | Medium |
| `stravinsky` | Sonnet 4.5 | Claude native | Moderate |
| `frontend` | Haiku | gemini-3-pro-high | Medium |
| `implementation-lead` | Sonnet | Claude native | Medium |
| `delphi` | Sonnet | gpt-5.2 | Expensive |
| `planner` | Opus | Claude native | Expensive |

### How It Works

```
User Request
     │
     ▼
┌─────────────┐
│ Haiku Agent │ ◄── Cheap wrapper, parses request
└─────────────┘
     │
     ▼
┌──────────────────┐
│ invoke_gemini()  │ ◄── Delegates ALL work to Gemini
│ invoke_openai()  │     or GPT via MCP tools
└──────────────────┘
     │
     ▼
┌─────────────┐
│   Results   │ ◄── Returned directly to caller
└─────────────┘
```

### Native Claude Work

Some agents run natively on Claude without delegation:

- **stravinsky:** Orchestration requires Claude's tool coordination
- **code-reviewer:** Deep code analysis benefits from Claude's reasoning
- **debugger:** Debugging requires Claude's step-by-step analysis
- **planner:** Complex planning uses Opus for superior reasoning

---

## Agent Details

### stravinsky (Orchestrator)

**Purpose:** Task orchestration, planning, goal-oriented execution

**Model:** Sonnet (native Claude work)

**Best for:**
- Breaking complex tasks into subtasks
- Coordinating multiple agents
- Ensuring task completion

**Example:**
```python
Task(
  subagent_type="stravinsky",
  prompt="Implement user authentication with JWT, including login, logout, and token refresh"
)
```

### planner (Pre-Implementation Planner)

**Purpose:** Create structured implementation plans before coding begins

**Model:** Opus (native Claude work, expensive)

**Best for:**
- Planning complex implementations before writing code
- Breaking down requirements into parallel and sequential tasks
- Identifying dependencies and potential blockers
- Creating agent delegation roadmaps

**Example:**
```python
Task(
  subagent_type="planner",
  prompt="Create a detailed implementation plan for adding OAuth2 authentication with Google and GitHub providers"
)
```

**Note:** Uses Claude Opus for superior reasoning about dependencies and parallelization.

### delphi (Strategic Advisor)

**Purpose:** Strategic technical advice, architecture review, hard debugging

**Model:** Sonnet wrapper -> gpt-5.2

**Best for:**
- Architecture decisions
- Complex debugging when stuck
- Code review and optimization
- Strategic planning

**Example:**
```python
Task(
  subagent_type="delphi",
  prompt="Review the authentication architecture and suggest improvements for scalability"
)
```

**Note:** Uses GPT-5.2 for strategic reasoning capabilities.

### dewey (Documentation Researcher)

**Purpose:** Documentation research, implementation examples, multi-repository analysis

**Model:** Haiku wrapper -> gemini-3-flash (thin wrapper)

**Best for:**
- Finding implementation examples
- Researching library usage
- Documentation lookup
- Cross-repo analysis

**Example:**
```python
Task(
  subagent_type="dewey",
  prompt="Find examples of React Query usage with infinite scroll pagination"
)
```

**Cost:** Cheap - uses Haiku to delegate to Gemini Flash.

### explore (Codebase Explorer)

**Purpose:** Codebase-wide search and structural analysis

**Model:** Haiku wrapper -> gemini-3-flash (thin wrapper)

**Best for:**
- "Where is X?" questions
- Finding all usages of something
- Understanding code structure
- Dependency analysis

**Example:**
```python
Task(
  subagent_type="explore",
  prompt="Find all places where the User model is modified"
)
```

**Cost:** Cheap - uses Haiku to delegate to Gemini Flash.

### frontend (UI/UX Engineer)

**Purpose:** UI/UX work, component design, prototyping

**Model:** Haiku wrapper -> gemini-3-pro-high (thin wrapper)

**Best for:**
- Component design
- UI implementation
- Styling and layout
- Accessibility improvements

**Example:**
```python
Task(
  subagent_type="frontend",
  prompt="Design a responsive dashboard layout with sidebar navigation"
)
```

**Cost:** Medium - uses Gemini Pro for higher quality UI work.

### document_writer (Technical Writer)

**Purpose:** Technical documentation and specification writing

**Best for:**
- API documentation
- README files
- Technical specifications
- User guides

**Example:**
```python
Task(
  subagent_type="document_writer",
  prompt="Write API documentation for the authentication endpoints"
)
```

### multimodal (Visual Analyst)

**Purpose:** Visual analysis of UI screenshots, diagrams, and images

**Best for:**
- Screenshot analysis
- UI/UX feedback from images
- Diagram interpretation
- Visual debugging

**Example:**
```python
Task(
  subagent_type="multimodal",
  prompt="Analyze this screenshot and identify accessibility issues"
)
```

### momus (Quality Gate)

**Purpose:** Quality gate guardian - validates code, research, and docs before approval.

**Model:** Haiku wrapper -> gemini-3-flash

**Best for:**
- Pre-commit validation (tests, linting)
- Research quality assessment
- Documentation completeness checks
- Pattern/anti-pattern detection

**Example:**
```python
Task(
  subagent_type="momus",
  prompt="Validate the quality of the recent auth implementation changes"
)
```

**Cost:** Cheap - uses Gemini Flash.

### research-lead (Research Coordinator)

**Purpose:** Coordinates research tasks by spawning explore/dewey agents and synthesizing findings.

**Model:** Haiku wrapper -> gemini-3-flash

**Best for:**
- Complex research topics requiring multiple sources
- Decomposing research goals into sub-tasks
- Synthesizing findings from multiple agents into a coherent brief

**Example:**
```python
Task(
  subagent_type="research-lead",
  prompt="Research how to implement OAuth2 with PKCE in FastAPI"
)
```

**Cost:** Cheap - uses Gemini Flash for synthesis.

### implementation-lead (Execution Coordinator)

**Purpose:** Coordinates implementation based on research briefs.

**Model:** Sonnet 4.5 (native)

**Best for:**
- Taking a research brief and producing working code
- Delegating specific tasks to frontend, debugger, and code-reviewer
- Verifying implementation with diagnostics

**Example:**
```python
Task(
  subagent_type="implementation-lead",
  prompt="Implement the OAuth2 flow based on the research brief"
)
```

**Cost:** Medium - uses Claude Sonnet for coordination.

---

## Choosing the Right Agent

### Decision Tree

```
Is it about finding/searching code?
  -> explore (cheap, Gemini Flash)

Is it about documentation or examples?
  -> dewey (cheap, Gemini Flash)

Is it about UI/frontend work?
  -> frontend (medium, Gemini Pro)

Is it about architecture or strategy?
  -> delphi (expensive, GPT-5.2)

Is it about writing documentation?
  -> document_writer

Is it about analyzing images/screenshots?
  -> multimodal

Is it a complex multi-step task?
  -> stravinsky (medium, native Sonnet)

Need a plan before implementing?
  -> planner (expensive, native Opus)
```

### Cost Optimization Strategy

**For exploration/research tasks:**
- Use `explore` and `dewey` liberally - they're cheap Haiku wrappers
- Spawn multiple in parallel for broad searches

**For complex reasoning:**
- Use `delphi` sparingly - it uses expensive GPT-5.2
- Reserve for architecture decisions and hard debugging

**For native Claude work:**
- `stravinsky` and `code-reviewer` run on Sonnet
- `planner` runs on Opus (most expensive)

### Parallel Agent Strategies

**Exploration Phase (Cheap):**
```python
Task(subagent_type="explore", prompt="Find models")
Task(subagent_type="explore", prompt="Find controllers")
Task(subagent_type="explore", prompt="Find tests")
```

**Research Phase (Cheap + Expensive):**
```python
Task(subagent_type="dewey", prompt="Research best practices")      # Cheap
Task(subagent_type="delphi", prompt="Review current architecture")   # Expensive
```

**Implementation Phase (Medium):**
```python
Task(subagent_type="stravinsky", prompt="Implement backend")
Task(subagent_type="frontend", prompt="Implement frontend")
```

---

## Agent Communication

Agents run independently but you can:

1. **Chain results:** Get output from one agent, pass to another
2. **Parallel execution:** Spawn multiple agents simultaneously
3. **Orchestrate:** Use `stravinsky` agent to coordinate others

### Hook Architecture

Stravinsky agents leverage a sophisticated hook system for delegation and control flow. For detailed information about:
- PreToolUse and PostToolUse hooks
- Delegation patterns and cost-based routing
- Extended thinking budgets
- Hook execution flow

See `.claude/agents/HOOKS.md` in the project root for comprehensive hook architecture documentation.

### Example: Full Workflow

```python
# Phase 1: Parallel exploration (all cheap Haiku->Gemini)
# Fire all simultaneously in ONE response:
Task(subagent_type="explore", prompt="Find all database models")
Task(subagent_type="explore", prompt="Find all API endpoints")
Task(subagent_type="dewey", prompt="Research REST best practices")

# Phase 2: Wait and collect (Task tool returns results directly)
# models = ... (from Task 1)
# api = ... (from Task 2)
# practices = ... (from Task 3)

# Phase 3: Strategic review (expensive GPT-5.2)
Task(
  subagent_type="delphi",
  prompt=f"Review this architecture:\nModels: {models}\nAPI: {api}\nBest practices: {practices}"
)
```

---

## Performance Tips

1. **Use `explore` and `dewey` liberally** - they're cheap Haiku->Gemini wrappers
2. **Unified LSP Performance** - All agents benefit from the unified, persistent LSP architecture. Tools like `lsp_hover` and `lsp_goto_definition` now use long-running servers, providing near-instant results by avoiding cold-start overhead and leveraging workspace-wide indexing caches.
3. **Batch related tasks** - spawn multiple explore agents together
3. **Use `agent_progress`** - monitor long-running agents
4. **Cancel stuck agents** - don't wait indefinitely
5. **Reserve `delphi` for hard problems** - it uses expensive GPT-5.2
6. **Use native Claude agents for coordination** - `stravinsky` for orchestration
