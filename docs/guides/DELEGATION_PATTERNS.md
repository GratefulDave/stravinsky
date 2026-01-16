# Parallel Delegation Patterns - The Complete Guide

## TL;DR

**CORRECT**: Fire all Task() calls in ONE response
**WRONG**: Sequential responses with Task() calls spread out

## Execution Context Matters

### Context 1: Native Subagent (RECOMMENDED)

**When**: Running as `.claude/agents/stravinsky.md` (automatic for complex tasks)
**Tool**: Use `Task()` for delegation

```python
# ✅ CORRECT: All Task calls in same response
Task(subagent_type="explore", prompt="Find auth...", description="Find auth")
Task(subagent_type="dewey", prompt="Research JWT...", description="Research JWT")
Task(subagent_type="code-reviewer", prompt="Review...", description="Review")
# Task tool returns results directly - synthesize and proceed
```

### Context 2: MCP Skill (LEGACY)

**When**: Explicitly invoked via `/strav` slash command
**Tool**: Use `agent_spawn()` for delegation

```python
# ✅ CORRECT: All agent_spawn calls in same response
agent_spawn(agent_type="explore", prompt="Find auth...", description="Find auth")
agent_spawn(agent_type="dewey", prompt="Research JWT...", description="Research JWT")
agent_spawn(agent_type="frontend", prompt="Build UI...", description="Build UI")
# Collect results later with agent_output()
```

---

## Pattern 1: Implementation with TODOs

### ✅ CORRECT (Native Subagent Context)

```
Step 1: Create todos
TodoWrite([
    {"title": "Research JWT best practices", "status": "pending"},
    {"title": "Find auth implementations", "status": "pending"},
    {"title": "Implement JWT validation", "status": "pending"}
])

Step 2: Delegate ALL independent todos in SAME response
Task(
    subagent_type="dewey",
    prompt="""Research JWT best practices from official docs.
    
    Focus on:
    - RS256 vs HS256 security
    - Token expiration strategies
    - Refresh token patterns
    
    Return: Best practices summary with citations""",
    description="JWT best practices"
)

Task(
    subagent_type="explore",
    prompt="""Find all JWT/auth implementations in the codebase.
    
    Return:
    - File paths with line numbers
    - Current authentication patterns
    - JWT validation logic""",
    description="Find auth code"
)

Step 3: Synthesize Task results
[Results are returned directly from Task tool - analyze and proceed]

Step 4: Implement JWT validation based on findings
[Use the gathered information to implement]

Step 5: Mark todos complete
TodoWrite([
    {"id": "...", "status": "completed"},
    {"id": "...", "status": "completed"},
    {"id": "...", "status": "completed"}
])
```

**Why this works:**
- Tasks fire in parallel immediately
- No waiting between task creation and delegation
- Results come back when ready
- Clear execution flow

### ❌ WRONG Pattern 1: Delayed Delegation

```
Step 1: Create todos
TodoWrite([...])
[Response ends here - WRONG!]

[Next response:]
Step 2: Start working on todo 1
TodoWrite([{"id": "abc", "status": "in_progress"}])
[Work on todo manually - WRONG!]

[Next response:]
Step 3: Now spawn an agent?
Task(...) - TOO LATE! Should have been parallel!
```

**Why this fails:**
- Sequential execution defeats parallelism
- Wastes time between responses
- No parallelism benefit
- User sees slow progress

### ❌ WRONG Pattern 2: Working Manually

```
Step 1: Create todos
TodoWrite([...])

Step 2: Do it yourself
Read("src/auth.py")
Grep("jwt", "**/*.py")
[Manual work when agents should handle it - WRONG!]
```

**Why this fails:**
- Orchestrator doing worker tasks
- No specialist agent optimization
- Slower than parallel agents
- Defeats multi-model routing

---

## Pattern 2: Exploratory Tasks (No TodoWrite)

### ✅ CORRECT (Native Subagent Context)

```
User: "Find authentication flow and error handling patterns"

[IMMEDIATE parallel delegation in same response:]
Task(
    subagent_type="explore",
    prompt="""Find authentication flow in the codebase.
    
    Return:
    - Entry points (login, auth middleware)
    - Token validation logic
    - Session management
    - File paths with line numbers""",
    description="Find auth flow"
)

Task(
    subagent_type="explore",
    prompt="""Find error handling patterns in the codebase.
    
    Return:
    - Error middleware/handlers
    - Exception classes
    - Error response formats
    - Logging patterns""",
    description="Find error handling"
)

[Continue in same response - synthesize Task results when available]
```

**Why this works:**
- No TodoWrite needed (exploratory, not implementation)
- Both tasks fire immediately in parallel
- Results synthesized when ready
- Fast turnaround

### ❌ WRONG: Manual Exploration

```
User: "Find authentication flow and error handling patterns"

Read("src/auth.py")
Grep("authenticate", "**/*.py")
Glob("**/*error*.py")
[Doing exploration manually - WRONG!]
```

**Why this fails:**
- Orchestrator doing specialist work
- Sequential file operations
- No semantic search capability
- Explore agent has better tools for this

---

## Pattern 3: Dependent vs Independent Tasks

### Task Independence Detection

**INDEPENDENT** tasks can run in parallel:
- No shared files (auth.py vs config.py)
- No data dependencies (research vs implementation)
- No ordering requirements (tests vs docs)

**DEPENDENT** tasks must run sequentially:
- Task B needs Task A's output
- Task B modifies same file as Task A
- Task B verifies Task A (tests after code)

### ✅ CORRECT: Mixed Dependencies

```
# INDEPENDENT tasks (fire in parallel):
TODO 1: "Research JWT best practices" (reads external docs)
TODO 2: "Find auth implementations" (reads codebase)
TODO 3: "Update README with auth docs" (writes README.md)

# ALL 3 can run in parallel - different sources/targets
Task(subagent_type="dewey", prompt="TODO 1...", description="JWT research")
Task(subagent_type="explore", prompt="TODO 2...", description="Find auth")
Task(subagent_type="explore", prompt="TODO 3...", description="Update README")

# DEPENDENT task (wait for above):
TODO 4: "Implement JWT validation using findings" (needs TODO 1 & 2 results)

# Fire after Tasks 1-3 complete:
[Synthesize results from Tasks 1-3]
[Implement based on findings]
```

### ❌ WRONG: Running Dependent Tasks in Parallel

```
# Task 2 DEPENDS on Task 1 output:
TODO 1: "Find all deprecated API usages" (produces file list)
TODO 2: "Update each file to new API" (needs file list from TODO 1)

# WRONG - firing both in parallel:
Task(subagent_type="explore", prompt="TODO 1...", description="Find deprecated")
Task(subagent_type="explore", prompt="TODO 2...", description="Update files")
# Task 2 will fail - it needs Task 1's results first!
```

---

## Pattern 4: ULTRAWORK Mode

**Trigger**: User says "ultrawork", "uw", "ultrawork", or "ulw"

### ✅ CORRECT: Maximum Parallelism

```
User: "ultrawork Find auth, error handling, and logging patterns"

[IMMEDIATE parallel spawn - minimum 2+ agents:]
Task(subagent_type="explore", prompt="Find auth patterns...", description="Auth")
Task(subagent_type="explore", prompt="Find error handling...", description="Errors")
Task(subagent_type="explore", prompt="Find logging patterns...", description="Logging")

[All fire in same response - NO manual work]
```

### ❌ WRONG: Not Enough Parallelism

```
User: "ultrawork Find auth flow"

[Only spawning 1 agent - not ultra enough!]
Task(subagent_type="explore", prompt="Find auth...", description="Auth")
# Should have broken into 2+ subtasks for more parallelism
```

---

## Pattern 5: Frontend Visual Changes

### ✅ CORRECT: Always Delegate to Frontend Agent

```
User: "Update button colors and add hover animations"

[ALWAYS delegate visual work to frontend specialist:]
Task(
    subagent_type="frontend",
    prompt="""Update UI components with visual changes.
    
    Changes:
    - Button colors: primary blue → brand purple
    - Add smooth hover transitions (200ms)
    - Ensure accessibility contrast
    
    Files: src/components/Button.tsx""",
    description="Update button styling"
)
```

### ❌ WRONG: Doing UI Work Yourself

```
User: "Update button colors and add hover animations"

Edit("src/components/Button.tsx", ...)
[Writing CSS/styling yourself - WRONG! Frontend agent specializes in this]
```

---

## Pattern 6: Architecture Decisions

### ✅ CORRECT: Consult Delphi After Failures

```
[After 2+ failed fix attempts:]
Task(
    subagent_type="delphi",
    prompt="""Analyze recurring payment processing race condition.
    
    SYMPTOMS:
    - 1 in 500 payments stuck in "pending"
    - No error logs
    - Only under high load
    
    FAILED FIXES:
    1. Increased transaction timeout (no effect)
    2. Added retry logic (caused duplicates)
    
    ANALYZE:
    - Possible race conditions
    - Root cause hypotheses
    - Testing strategy
    - Recommended fix""",
    description="Debug payment race"
)
```

### ❌ WRONG: Keep Trying Same Approaches

```
[After 2 failures:]
Read("src/payment.py")
Edit("src/payment.py", ...) # Try another random fix
[Should have consulted Delphi after 2 failures - WRONG!]
```

---

## Key Principles

### 1. PARALLEL-FUWT (Fire Upon Writing TODOs)

After TodoWrite, your **VERY NEXT ACTION** must be Task() calls for each independent TODO.

**NEVER**:
- End response without Task calls
- Mark todos in_progress first
- Work on todos yourself
- Wait for user confirmation

### 2. Same Response = Parallel Execution

All independent Task() calls MUST be in the **SAME response block**.

```
✅ CORRECT:
Task(...)
Task(...)
Task(...)
# All fire simultaneously

❌ WRONG:
Task(...) [Response 1]
[Wait]
Task(...) [Response 2]
# Sequential = defeats parallelism
```

### 3. Independence Test

**"Can Task B start before Task A finishes WITHOUT reading Task A's output or touching Task A's files?"**

- YES → PARALLEL (fire simultaneously)
- NO → SEQUENTIAL (chain with →)

### 4. Verification Always

After delegation completes:
- Read results from Task tool
- Verify deliverables match expected outcome
- Run lsp_diagnostics on changed files
- Run tests if applicable

**NEVER assume success without verification.**

---

## Checklist: Before Responding

- [ ] Did I identify all independent subtasks?
- [ ] Am I firing ALL Task() calls in THIS response?
- [ ] Am I using the right context (Task vs agent_spawn)?
- [ ] Did I check for dependencies (sequential vs parallel)?
- [ ] Am I delegating to the right specialist (explore vs dewey vs delphi)?
- [ ] Did I include all 7 sections in delegation prompt?
- [ ] Will I verify results after Task completes?

---

## Common Mistakes & Fixes

| Mistake | Why Bad | Fix |
|---------|---------|-----|
| Ending response after TodoWrite | No parallelism, sequential execution | Fire all Task() calls in same response |
| Spawning agents in separate responses | Sequential, wastes time | All Task() calls in ONE response |
| Working manually (Read/Grep) | Orchestrator doing worker job | Delegate to explore/dewey agents |
| Not checking dependencies | Parallel tasks fail needing prior output | Classify as independent/dependent first |
| Using wrong tool (Task in /strav) | Context mismatch | Task for native agents, agent_spawn for /strav |
| Single agent in ULTRAWORK mode | Not ultra enough | Always spawn 2+ agents minimum |
| Skipping verification | Agents can fail silently | Always verify Task results |

---

## Success Metrics

**Good parallel delegation:**
- 2+ Task() calls in single response
- All independent tasks fire simultaneously
- Results synthesized when ready
- Fast turnaround time

**Bad sequential execution:**
- Single Task() per response
- Manual work between delegations
- Slow progress with many back-and-forths
- User sees delays

---

## Summary

**The Golden Rule**: After TodoWrite (or identifying exploratory work), spawn ALL independent Task() calls in the SAME response. NEVER end your response without delegation when parallel work is possible.

**Context Awareness**: Use `Task()` in native subagent context (recommended), `agent_spawn()` in /strav MCP context (legacy).

**Verify Everything**: Agents can fail. Always check results, run diagnostics, validate output before marking complete.
