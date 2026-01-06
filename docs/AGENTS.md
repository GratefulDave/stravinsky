# Stravinsky Agent Types

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
| `explore` | Haiku | gemini-3-flash | Cheap |
| `dewey` | Haiku | gemini-3-flash | Cheap |
| `frontend` | Haiku | gemini-3-pro-high | Medium |
| `delphi` | Sonnet | gpt-5.2-medium | Expensive |
| `code-reviewer` | Sonnet | Claude native | Medium |
| `debugger` | Sonnet | Claude native | Medium |
| `stravinsky` | Sonnet | Claude native | Medium |
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
```
agent_spawn(
  "Implement user authentication with JWT, including login, logout, and token refresh",
  "stravinsky",
  "Auth implementation"
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
```
agent_spawn(
  "Create a detailed implementation plan for adding OAuth2 authentication with Google and GitHub providers",
  "planner",
  "Plan OAuth implementation"
)
```

**Note:** Uses Claude Opus for superior reasoning about dependencies and parallelization.

### delphi (Strategic Advisor)

**Purpose:** Strategic technical advice, architecture review, hard debugging

**Model:** Sonnet wrapper -> gpt-5.2-medium

**Best for:**
- Architecture decisions
- Complex debugging when stuck
- Code review and optimization
- Strategic planning

**Example:**
```
agent_spawn(
  "Review the authentication architecture and suggest improvements for scalability",
  "delphi",
  "Auth review"
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
```
agent_spawn(
  "Find examples of React Query usage with infinite scroll pagination",
  "dewey",
  "React Query research"
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
```
agent_spawn(
  "Find all places where the User model is modified",
  "explore",
  "User model usage"
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
```
agent_spawn(
  "Design a responsive dashboard layout with sidebar navigation",
  "frontend",
  "Dashboard design"
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
```
agent_spawn(
  "Write API documentation for the authentication endpoints",
  "document_writer",
  "API docs"
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
```
agent_spawn(
  "Analyze this screenshot and identify accessibility issues",
  "multimodal",
  "A11y analysis"
)
```

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
```
agent_spawn("Find models", "explore", "Models")
agent_spawn("Find controllers", "explore", "Controllers")
agent_spawn("Find tests", "explore", "Tests")
```

**Research Phase (Cheap + Expensive):**
```
agent_spawn("Research best practices", "dewey", "Research")      # Cheap
agent_spawn("Review current architecture", "delphi", "Review")   # Expensive
```

**Implementation Phase (Medium):**
```
agent_spawn("Implement backend", "stravinsky", "Backend")
agent_spawn("Implement frontend", "frontend", "Frontend")
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

```
# Phase 1: Parallel exploration (all cheap Haiku->Gemini)
explore_models = agent_spawn("Find all database models", "explore", "Models")
explore_api = agent_spawn("Find all API endpoints", "explore", "API")
research = agent_spawn("Research REST best practices", "dewey", "Research")

# Phase 2: Wait and collect
models = agent_output(explore_models)
api = agent_output(explore_api)
practices = agent_output(research)

# Phase 3: Strategic review (expensive GPT-5.2)
review = agent_spawn(
  f"Review this architecture:\nModels: {models}\nAPI: {api}\nBest practices: {practices}",
  "delphi",
  "Architecture review"
)
```

---

## Performance Tips

1. **Use `explore` and `dewey` liberally** - they're cheap Haiku->Gemini wrappers
2. **Batch related tasks** - spawn multiple explore agents together
3. **Use `agent_progress`** - monitor long-running agents
4. **Cancel stuck agents** - don't wait indefinitely
5. **Reserve `delphi` for hard problems** - it uses expensive GPT-5.2
6. **Use native Claude agents for coordination** - `stravinsky` for orchestration
