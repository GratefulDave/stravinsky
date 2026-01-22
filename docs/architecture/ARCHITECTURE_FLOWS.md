# Stravinsky Architecture Flows and Diagrams

Quick visual reference for how Stravinsky's 7-phase orchestration and parallel enforcement work.

**Updated**: 2026-01-22

---

## Flow 1: Complete 7-Phase Orchestration Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────┐
│ USER SUBMITS REQUEST                                                      │
│ Example: "Implement authentication with OAuth and add tests"              │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: CLASSIFY                                                         │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ - Analyze query type (implementation, research, debug, etc.)         │ │
│ │ - Determine scope (single file, multi-file, architectural)          │ │
│ │ - Identify required specialists                                      │ │
│ │ - Output: query_classification artifact                              │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: CONTEXT                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ - Select search strategy based on classification                     │ │
│ │   - Pattern queries -> grep_search, ast_grep_search                 │ │
│ │   - Conceptual queries -> semantic_search                           │ │
│ │   - Symbol queries -> lsp_workspace_symbols                         │ │
│ │ - Gather relevant code context                                       │ │
│ │ - Output: context_summary artifact                                   │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: WISDOM (Optional)                                                │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ - Load .stravinsky/wisdom.md if exists                              │ │
│ │ - Inject project-specific learnings into context                     │ │
│ │ - Include past failures, gotchas, patterns                          │ │
│ │ - Skip if no wisdom file exists                                      │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: PLAN (with Critique Loop)                                        │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ - Create strategic plan for task execution                           │ │
│ │ - Generate critique: "3 ways this could fail"                       │ │
│ │ - Iterate up to 3 times for refinement                              │ │
│ │ - Output: plan.md artifact                                           │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                             ↑                                             │
│                             │ (max 3 critique iterations)                 │
│                             │                                             │
└───────────────────────┬─────┴────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: VALIDATE                                                         │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ - Validate plan against project rules                                │ │
│ │ - Check for constraint violations                                    │ │
│ │ - Verify feasibility                                                 │ │
│ │ - If fails: return to PLAN phase                                    │ │
│ │ - Output: validation_result artifact                                 │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 6: DELEGATE (TaskGraph Construction)                                │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ - Build TaskGraph from plan                                          │ │
│ │ - Identify independent tasks (no dependencies)                       │ │
│ │ - Group tasks into execution waves                                   │ │
│ │ - Assign agent types and models                                      │ │
│ │ - Create DelegationEnforcer                                          │ │
│ │ - Output: delegation_targets, task_graph artifacts                   │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  TaskGraph Example:                                                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                           │
│  │search_auth │ │research_   │ │review_     │  Wave 1                   │
│  │(explore)   │ │patterns    │ │security    │  (all parallel)           │
│  │deps=[]     │ │(dewey)     │ │(code-rev)  │                           │
│  └─────┬──────┘ └─────┬──────┘ └────────────┘                           │
│        │              │                                                   │
│        └──────┬───────┘                                                   │
│               ↓                                                           │
│        ┌────────────┐                                                     │
│        │implement_  │  Wave 2                                            │
│        │feature     │  (after Wave 1)                                    │
│        │(frontend)  │                                                     │
│        │deps=[a,b]  │                                                     │
│        └─────┬──────┘                                                     │
│              ↓                                                            │
│        ┌────────────┐                                                     │
│        │write_tests │  Wave 3                                            │
│        │(code-rev)  │  (after Wave 2)                                    │
│        │deps=[impl] │                                                     │
│        └────────────┘                                                     │
│                                                                           │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 7: EXECUTE (Parallel Enforcement)                                   │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ FOR each wave in TaskGraph:                                          │ │
│ │   - Spawn ALL wave tasks in parallel (<500ms window)                │ │
│ │   - DelegationEnforcer validates parallel spawning                  │ │
│ │   - If sequential spawning detected: ParallelExecutionError         │ │
│ │   - Collect results from all wave tasks                             │ │
│ │   - Advance to next wave after completion                           │ │
│ │ - Output: execution_result artifact                                  │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                             ↑                                             │
│                             │ (retry loop if needed)                      │
│                             │                                             │
└───────────────────────┬─────┴────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 8: VERIFY                                                           │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ - Synthesize results from all agents                                 │ │
│ │ - Verify task completion                                             │ │
│ │ - Run quality checks (lsp_diagnostics, tests)                       │ │
│ │ - Prepare final response to user                                     │ │
│ │ - Can start new CLASSIFY cycle if needed                            │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Flow 2: Parallel Execution Enforcement

```
┌──────────────────────────────────────────────────────────────────────────┐
│ PARALLEL EXECUTION ENFORCEMENT                                            │
│                                                                           │
│ Wave 1 Tasks: [search_auth, research_patterns, review_security]          │
│ All have deps=[] (independent)                                            │
│                                                                           │
│ CORRECT EXECUTION:                                                        │
│ ════════════════════════════════════════════════════════════════════════ │
│                                                                           │
│ t=0ms     agent_spawn("search_auth", "explore", task_graph_id="a")       │
│ t=50ms    agent_spawn("research_patterns", "dewey", task_graph_id="b")   │
│ t=100ms   agent_spawn("review_security", "code-rev", task_graph_id="c")  │
│                                                                           │
│ Time spread: 100ms < 500ms limit                                          │
│ Result: DelegationEnforcer.check_parallel_compliance() = True            │
│                                                                           │
│ ════════════════════════════════════════════════════════════════════════ │
│                                                                           │
│ INCORRECT EXECUTION (BLOCKED):                                            │
│ ════════════════════════════════════════════════════════════════════════ │
│                                                                           │
│ t=0ms     agent_spawn("search_auth", "explore", task_graph_id="a")       │
│ t=0ms     agent_output("a", block=True)  <-- WAIT for result             │
│ t=5000ms  agent_spawn("research_patterns", "dewey", task_graph_id="b")   │
│                                                                           │
│ Time spread: 5000ms > 500ms limit                                         │
│ Result: ParallelExecutionError raised!                                   │
│                                                                           │
│ Error: "Tasks in wave were not spawned in parallel.                       │
│         Time spread: 5000ms > 500ms limit.                                │
│         Independent tasks MUST be spawned simultaneously."                │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Flow 3: Agent Delegation with Injected Prompts

```
┌──────────────────────────────────────────────────────────────────────────┐
│ AGENT DELEGATION FLOW                                                     │
│                                                                           │
│ Orchestrator calls:                                                       │
│   agent_spawn(                                                            │
│       prompt="Find all authentication implementations",                   │
│       agent_type="explore",                                               │
│       task_graph_id="search_auth"                                         │
│   )                                                                       │
│                                                                           │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ AGENT MANAGER (agent_manager.py)                                          │
│                                                                           │
│ 1. Validate spawn with DelegationEnforcer                                │
│    enforcer.validate_spawn("search_auth") -> (True, None)                │
│                                                                           │
│ 2. Get delegation prompt                                                  │
│    delegation_prompt = get_agent_delegation_prompt("explore")            │
│                                                                           │
│    Returns:                                                               │
│    ┌────────────────────────────────────────────────────────────────────┐│
│    │ ## CRITICAL: DELEGATE TO GEMINI IMMEDIATELY                        ││
│    │                                                                     ││
│    │ You are the Explore agent. Your ONLY job is to delegate ALL        ││
│    │ work to Gemini Flash with full tool access.                        ││
│    │                                                                     ││
│    │ **IMMEDIATELY** call `mcp__stravinsky__invoke_gemini_agentic`:     ││
│    │ - model: gemini-3-flash                                            ││
│    │ - prompt: The task description                                     ││
│    │ - max_turns: 10                                                    ││
│    │                                                                     ││
│    │ **CRITICAL**: Use invoke_gemini_agentic NOT invoke_gemini.         ││
│    │ The agentic version enables tool calling.                          ││
│    └────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│ 3. Build full system prompt                                               │
│    system_prompt = delegation_prompt + agent_context + task_prompt       │
│                                                                           │
│ 4. Spawn Claude CLI with injected prompt                                 │
│    claude -p "$full_prompt" --model sonnet                               │
│                                                                           │
│ 5. Record spawn with enforcer                                             │
│    enforcer.record_spawn("search_auth", "agent_abc123")                  │
│                                                                           │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ EXPLORE AGENT (Claude CLI subprocess)                                     │
│                                                                           │
│ Receives injected delegation prompt, IMMEDIATELY calls:                   │
│                                                                           │
│   mcp__stravinsky__invoke_gemini_agentic(                                │
│       model="gemini-3-flash",                                             │
│       prompt="Search the codebase for authentication implementations     │
│               using semantic_search, grep_search, ast_grep_search...",   │
│       max_turns=10                                                        │
│   )                                                                       │
│                                                                           │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ GEMINI FLASH (via invoke_gemini_agentic)                                  │
│                                                                           │
│ Gemini executes multi-turn search workflow:                               │
│   Turn 1: grep_search("auth", "*.py")                                    │
│   Turn 2: ast_grep_search("class $_ extends AuthProvider")              │
│   Turn 3: semantic_search("OAuth token handling")                        │
│   Turn 4: lsp_find_references("authenticate")                            │
│   Turn 5: Synthesize results                                              │
│                                                                           │
│ Returns: Comprehensive search results                                     │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Flow 4: TaskGraph Execution Waves

```
TASKGRAPH EXECUTION TIMELINE
════════════════════════════════════════════════════════════════════════════

Time →
─────────────────────────────────────────────────────────────────────────→

Wave 1: Independent Tasks (parallel)
┌────────────────────────────────────────────────────────────────────────┐
│  t=0ms                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                   │
│  │ search_auth  │ │ research_    │ │ review_      │                   │
│  │ (explore)    │ │ patterns     │ │ security     │                   │
│  │ Gemini Flash │ │ (dewey)      │ │ (code-rev)   │                   │
│  │ CHEAP        │ │ Gemini Flash │ │ Gemini Flash │                   │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘                   │
│         │                │                │                            │
│         └────────────────┼────────────────┘                            │
│                          │                                              │
│  DelegationEnforcer validates: all spawned within 500ms               │
│                          │                                              │
│         ┌────────────────┼────────────────┐                            │
│         ↓                ↓                ↓                            │
│  t=8000ms (agents complete)                                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                   │
│  │ Auth code    │ │ OAuth best   │ │ Security     │                   │
│  │ locations    │ │ practices    │ │ review       │                   │
│  │ found        │ │ documented   │ │ complete     │                   │
│  └──────────────┘ └──────────────┘ └──────────────┘                   │
│                                                                        │
│  enforcer.advance_wave() -> Wave 2                                    │
└────────────────────────────────────────────────────────────────────────┘

Wave 2: Dependent Task
┌────────────────────────────────────────────────────────────────────────┐
│  t=8100ms                                                               │
│  ┌──────────────────────────────────────────────────────┐              │
│  │ implement_feature                                     │              │
│  │ (frontend)                                            │              │
│  │ Gemini Pro High                                       │              │
│  │ MEDIUM                                                │              │
│  │ deps=[search_auth, research_patterns] <- SATISFIED   │              │
│  └───────────────────────┬──────────────────────────────┘              │
│                          │                                              │
│  t=25000ms (implementation complete)                                   │
│  ┌──────────────────────────────────────────────────────┐              │
│  │ OAuth UI components implemented                       │              │
│  │ Token handling added                                  │              │
│  │ Error states covered                                  │              │
│  └──────────────────────────────────────────────────────┘              │
│                                                                        │
│  enforcer.advance_wave() -> Wave 3                                    │
└────────────────────────────────────────────────────────────────────────┘

Wave 3: Final Task
┌────────────────────────────────────────────────────────────────────────┐
│  t=25100ms                                                              │
│  ┌──────────────────────────────────────────────────────┐              │
│  │ write_tests                                           │              │
│  │ (code-reviewer)                                       │              │
│  │ Gemini Flash                                          │              │
│  │ CHEAP                                                 │              │
│  │ deps=[implement_feature] <- SATISFIED                │              │
│  └───────────────────────┬──────────────────────────────┘              │
│                          │                                              │
│  t=35000ms (tests complete)                                            │
│  ┌──────────────────────────────────────────────────────┐              │
│  │ Unit tests added for OAuth flow                       │              │
│  │ Integration tests for token refresh                   │              │
│  │ Edge cases covered                                    │              │
│  └──────────────────────────────────────────────────────┘              │
│                                                                        │
│  enforcer.advance_wave() -> False (all waves complete)                │
└────────────────────────────────────────────────────────────────────────┘

Total execution: 35 seconds (vs 50+ seconds if sequential)
Cost savings: Wave 1 ran 3 cheap agents in parallel
```

---

## Flow 5: Phase Artifact Requirements

```
PHASE ARTIFACT FLOW
════════════════════════════════════════════════════════════════════════════

Phase                 Required to Enter    Produces
─────────────────────────────────────────────────────────────────────────────

[1] CLASSIFY          (none - entry)       → query_classification
        │                                         │
        └─────────────────────────────────────────┘
                                                  ↓
[2] CONTEXT           query_classification → context_summary
        │                                         │
        └─────────────────────────────────────────┘
                                                  ↓
[3] WISDOM            context_summary      → (wisdom injected)
        │             (optional phase)            │
        └─────────────────────────────────────────┘
                                                  ↓
[4] PLAN              (none - wisdom opt)  → plan.md
        │                     ↑                   │
        │                     │ (critique loop)   │
        └─────────────────────┘───────────────────┘
                                                  ↓
[5] VALIDATE          plan.md              → validation_result
        │                     ↑                   │
        │                     │ (if fails)        │
        └─────────────────────┘───────────────────┘
                                                  ↓
[6] DELEGATE          validation_result    → delegation_targets
        │                                  → task_graph
        │                                         │
        └─────────────────────────────────────────┘
                                                  ↓
[7] EXECUTE           delegation_targets   → execution_result
        │             task_graph                  │
        │                     ↑                   │
        │                     │ (retry loop)      │
        └─────────────────────┘───────────────────┘
                                                  ↓
[8] VERIFY            execution_result     → (final synthesis)
        │                                         │
        └───────── (can start new cycle) ─────────┘
```

---

## Flow 6: Agent Cost Tier Routing

```
AGENT COST-BASED ROUTING
════════════════════════════════════════════════════════════════════════════

Request: "Implement feature with tests and documentation"

Orchestrator Decisions:
─────────────────────────────────────────────────────────────────────────────

ALWAYS PARALLEL (Cheap - Wave 1):
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   EXPLORE    │    │    DEWEY     │    │  CODE-REV    │              │
│  │              │    │              │    │              │              │
│  │ Gemini Flash │    │ Gemini Flash │    │ Gemini Flash │              │
│  │              │    │ + WebSearch  │    │              │              │
│  │ Cost: FREE   │    │ Cost: CHEAP  │    │ Cost: CHEAP  │              │
│  │              │    │              │    │              │              │
│  │ "Find code"  │    │ "Research"   │    │ "Review"     │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                          │
│  All spawn within 500ms window - PARALLEL ENFORCED                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

BLOCKING WHEN NEEDED (Medium - Wave 2):
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌───────────────────────────────┐                                      │
│  │          FRONTEND             │                                      │
│  │                               │                                      │
│  │      Gemini 3 Pro High        │                                      │
│  │                               │                                      │
│  │        Cost: MEDIUM           │                                      │
│  │                               │                                      │
│  │   "Implement UI components"   │                                      │
│  │                               │                                      │
│  │  BLOCKING - waits for Wave 1  │                                      │
│  └───────────────────────────────┘                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

STRATEGIC ONLY (Expensive - When Needed):
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌───────────────────────────────┐                                      │
│  │           DELPHI              │     Only invoked:                    │
│  │                               │     - After 3+ failures              │
│  │          GPT-5.2              │     - For architecture decisions     │
│  │                               │     - When explicitly requested      │
│  │       Cost: EXPENSIVE         │                                      │
│  │                               │                                      │
│  │  "Strategic architecture"     │                                      │
│  │                               │                                      │
│  │  BLOCKING - extended thinking │                                      │
│  └───────────────────────────────┘                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Flow 7: DelegationEnforcer State Machine

```
DELEGATIONENFORCER STATE MACHINE
════════════════════════════════════════════════════════════════════════════

                    ┌─────────────────────────────────────┐
                    │ DelegationEnforcer.__post_init__()  │
                    │                                     │
                    │ - Compute execution waves           │
                    │ - Initialize _current_wave = 0      │
                    │ - Log wave structure                │
                    └─────────────────┬───────────────────┘
                                      │
                                      ↓
              ┌─────────────────────────────────────────────┐
              │ get_current_wave() -> [task_a, task_b, ...]  │
              └─────────────────────┬───────────────────────┘
                                    │
                                    ↓
     ┌──────────────────────────────────────────────────────────────┐
     │ FOR each task in current wave:                               │
     │   validate_spawn(task_id)                                    │
     │   ├─ Is task in current wave? Yes -> (True, None)           │
     │   ├─ Is task in future wave? Yes -> (False, "unmet deps")   │
     │   └─ Unknown task? -> (False, "unknown task")               │
     └────────────────────────────┬─────────────────────────────────┘
                                  │
                                  ↓
     ┌──────────────────────────────────────────────────────────────┐
     │ record_spawn(task_id, agent_task_id)                         │
     │   - Append (task_id, timestamp) to _spawn_batch             │
     │   - Mark task as SPAWNED in TaskGraph                        │
     └────────────────────────────┬─────────────────────────────────┘
                                  │
                                  ↓
     ┌──────────────────────────────────────────────────────────────┐
     │ All wave tasks spawned?                                      │
     │   YES -> check_parallel_compliance()                        │
     │          ├─ Time spread < 500ms? -> (True, None)           │
     │          └─ Time spread > 500ms? -> (False, "not parallel") │
     │                                      │                       │
     │                                      ↓                       │
     │                        If strict=True: raise ParallelError  │
     └────────────────────────────┬─────────────────────────────────┘
                                  │
                                  ↓
     ┌──────────────────────────────────────────────────────────────┐
     │ All wave tasks completed?                                    │
     │   YES -> advance_wave()                                     │
     │          ├─ _current_wave += 1                              │
     │          ├─ Clear _spawn_batch                              │
     │          └─ Return: more waves? True/False                  │
     └────────────────────────────┬─────────────────────────────────┘
                                  │
                                  ↓
     ┌──────────────────────────────────────────────────────────────┐
     │ More waves?                                                  │
     │   YES -> Continue with next wave                            │
     │   NO  -> All execution complete                             │
     └──────────────────────────────────────────────────────────────┘
```

---

## Flow 8: OrchestratorState Transitions

```
ORCHESTRATORSTATE TRANSITION VALIDATION
════════════════════════════════════════════════════════════════════════════

transition_to(next_phase) Flow:
─────────────────────────────────────────────────────────────────────────────

                    ┌────────────────────────────┐
                    │ transition_to(next_phase)  │
                    └─────────────┬──────────────┘
                                  │
                                  ↓
              ┌──────────────────────────────────────────┐
              │ 1. Validate transition is allowed        │
              │    VALID_TRANSITIONS[current] contains   │
              │    next_phase?                           │
              │    ├─ YES -> continue                   │
              │    └─ NO  -> raise ValueError           │
              └─────────────────┬────────────────────────┘
                                │
                                ↓
              ┌──────────────────────────────────────────┐
              │ 2. Check artifact requirements           │
              │    (if strict_mode=True)                 │
              │    PHASE_REQUIREMENTS[next_phase] all    │
              │    present in artifacts?                 │
              │    ├─ YES -> continue                   │
              │    └─ NO  -> raise ValueError           │
              │           "Missing: [list of artifacts]" │
              └─────────────────┬────────────────────────┘
                                │
                                ↓
              ┌──────────────────────────────────────────┐
              │ 3. Check critique loop limit             │
              │    (if next_phase=PLAN from VALIDATE)    │
              │    critique_count < max_critiques?       │
              │    ├─ YES -> increment critique_count   │
              │    └─ NO  -> raise ValueError           │
              │           "Max critiques reached"        │
              └─────────────────┬────────────────────────┘
                                │
                                ↓
              ┌──────────────────────────────────────────┐
              │ 4. Check phase gates                     │
              │    (if enable_phase_gates=True)          │
              │    approver() returns True?              │
              │    ├─ YES -> continue                   │
              │    └─ NO  -> raise PermissionError      │
              └─────────────────┬────────────────────────┘
                                │
                                ↓
              ┌──────────────────────────────────────────┐
              │ 5. Execute transition                    │
              │    - history.append(current_phase)      │
              │    - current_phase = next_phase         │
              │    - Log transition                      │
              │    - Return True                         │
              └──────────────────────────────────────────┘
```

---

## Flow 9: Phase Visualization

```
PHASE PROGRESS VISUALIZATION
════════════════════════════════════════════════════════════════════════════

format_phase_progress(OrchestrationPhase.DELEGATE) returns:

  [Phase 6/8: DELEGATE] ━━━━━●──

Legend:
  ━  = Completed phase (green)
  ●  = Current phase (cyan)
  ─  = Pending phase (gray)


display_agent_execution("explore", "gemini-3-flash", "Find auth") returns:

  EXPLORE -> gemini-3-flash
     Task: Find auth implementations in codebase


display_parallel_batch_header(3) returns:

  ══════════════════════════════════════════════════
  PARALLEL DELEGATION (3 agents)
  ══════════════════════════════════════════════════
```

---

## Summary

The 7-phase orchestration with TaskGraph and DelegationEnforcer provides:

1. **Structured Workflow**: Clear phases with artifact requirements
2. **Hard Parallel Enforcement**: Independent tasks MUST run in parallel
3. **Cost Optimization**: Cheap agents run in parallel, expensive agents only when needed
4. **Cross-Repo Compatibility**: Delegation prompts injected at spawn time
5. **Audit Trail**: Full transition logging and enforcement status

---

**Last Updated**: 2026-01-22
**Architecture Version**: 7-Phase Orchestration with Hard Parallel Enforcement
