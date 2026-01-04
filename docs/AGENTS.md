# Stravinsky Agent Types

Detailed guide to specialized agent configurations.

---

## Overview

Stravinsky provides 7 specialized agent types, each with a unique system prompt optimized for specific tasks.

**All agents run via Claude CLI** using Claude's default model. Agents have full tool access and can invoke Stravinsky MCP tools (`invoke_gemini`, `invoke_openai`) if they need to use other models.

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

## Agent Details

### stravinsky (Orchestrator)

**Purpose:** Task orchestration, planning, goal-oriented execution

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

### dewey (Documentation Researcher)

**Purpose:** Documentation research, implementation examples, multi-repository analysis

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

### explore (Codebase Explorer)

**Purpose:** Codebase-wide search and structural analysis

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

### frontend (UI/UX Engineer)

**Purpose:** UI/UX work, component design, prototyping

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
  → explore

Is it about documentation or examples?
  → dewey

Is it about UI/frontend work?
  → frontend

Is it about architecture or strategy?
  → delphi

Is it about writing documentation?
  → document_writer

Is it about analyzing images/screenshots?
  → multimodal

Is it a complex multi-step task?
  → stravinsky

Need a plan before implementing?
  → planner
```

### Parallel Agent Strategies

**Exploration Phase:**
```
agent_spawn("Find models", "explore", "Models")
agent_spawn("Find controllers", "explore", "Controllers")
agent_spawn("Find tests", "explore", "Tests")
```

**Research Phase:**
```
agent_spawn("Research best practices", "dewey", "Research")
agent_spawn("Review current architecture", "delphi", "Review")
```

**Implementation Phase:**
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

### Example: Full Workflow

```
# Phase 1: Parallel exploration
explore_models = agent_spawn("Find all database models", "explore", "Models")
explore_api = agent_spawn("Find all API endpoints", "explore", "API")
research = agent_spawn("Research REST best practices", "dewey", "Research")

# Phase 2: Wait and collect
models = agent_output(explore_models)
api = agent_output(explore_api)
practices = agent_output(research)

# Phase 3: Strategic review
review = agent_spawn(
  f"Review this architecture:\nModels: {models}\nAPI: {api}\nBest practices: {practices}",
  "delphi",
  "Architecture review"
)
```

---

## Performance Tips

1. **Use `explore` for quick searches** - it's optimized for speed
2. **Batch related tasks** - spawn multiple explore agents together
3. **Use `agent_progress`** - monitor long-running agents
4. **Cancel stuck agents** - don't wait indefinitely
