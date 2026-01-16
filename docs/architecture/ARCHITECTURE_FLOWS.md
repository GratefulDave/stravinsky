# Stravinsky Architecture Flows & Diagrams

Quick visual reference for how Stravinsky's components interact.

---

## Flow 1: Complete Request Lifecycle (With Hooks)

```
┌──────────────────────────────────────────────────────────┐
│ USER SUBMITS REQUEST                                     │
│ Example: "Find all authentication implementations"       │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│ UserPromptSubmit Hook (if implemented)                   │
│ ├─ Inject CLAUDE.md rules                               │
│ ├─ Add project context (git, todos)                      │
│ ├─ Enable semantic search if available                  │
│ └─ Preprocess prompt                                     │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│ Claude Code AUTO-DELEGATES                               │
│ Matches stravinsky agent description → launches subagent │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│ STRAVINSKY ORCHESTRATOR PROCESSES                        │
│ ├─ Classify request type                                 │
│ ├─ Create TodoWrite([search auth, analyze patterns])    │
│ ├─ Determine delegation strategy                         │
│ └─ Prepare Task() calls                                  │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│ PreToolUse Hook FIRES (if implemented)                   │
│ ├─ Intercept: Read, Grep, Bash, Glob tools             │
│ ├─ Check: Is this a complex search?                      │
│ │          (AST pattern? Multi-file? Semantic?)          │
│ ├─ Decision:                                             │
│ │  ├─ ALLOW: Simple lookup → native tool executes       │
│ │  └─ BLOCK: Complex → exit code 2, trigger delegation  │
│ └─ Orchestrator sees block, uses Task() instead         │
└───────────────────────┬────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        ↓                               ↓
    ┌─────────────┐           ┌──────────────────┐
    │ NATIVE TOOL │           │ TASK DELEGATION  │
    │ (simple)    │           │ (complex)        │
    │             │           │                  │
    │ Example:    │           │ Task(            │
    │ Read a      │           │   subagent_type= │
    │ specific    │           │   "explore",     │
    │ file        │           │   prompt="Find   │
    │             │           │   all auth       │
    │ ↓           │           │   implementations"
    │ Executes    │           │ )                │
    │ immediately │           │                  │
    └──────┬──────┘           │ ↓                │
           │                  │                  │
           │                  │ Explore Agent   │
           │                  │ ├─ Receive task │
           │                  │ ├─ Run searches │
           │                  │ │ (grep, AST,   │
           │                  │ │  semantic,    │
           │                  │ │  lsp)         │
           │                  │ ├─ Synthesize   │
           │                  │ │  results      │
           │                  │ └─ Return to    │
           │                  │    orchestrator │
           │                  └──────┬──────────┘
           │                         │
           └───────────────┬─────────┘
                           ↓
          ┌────────────────────────────────┐
          │ PostToolUse Hook FIRES         │
          │ (if implemented)               │
          │ ├─ Detect Task() completion   │
          │ ├─ Log agent_type + result    │
          │ ├─ Aggregate specialist work  │
          │ └─ Signal synthesis phase     │
          └──────────────┬─────────────────┘
                         │
                         ↓
          ┌────────────────────────────────┐
          │ ORCHESTRATOR SYNTHESIZES       │
          │ ├─ Combine results            │
          │ ├─ Answer the original query  │
          │ ├─ Update TodoWrite           │
          │ └─ Respond to user            │
          └────────────────────────────────┘
```

---

## Flow 2: Tool Selection Decision Tree

```
                    ┌─ QUERY RECEIVED ─┐
                    │   Example: "Find  │
                    │   auth logic"     │
                    └────────┬──────────┘
                             │
                             ↓
                 ┌─────────────────────────┐
                 │ Is it about FILE PATHS? │
                 └────────┬────────┬───────┘
                          │        │
                        YES│        │NO
                          ↓        │
                    glob_files     │
                          │        │
                          ↓        ↓
                  ┌─────────────────────────┐
                  │ EXACT SYNTAX present?   │
                  │ (@decorator, class,     │
                  │ function())             │
                  └────────┬────────┬───────┘
                           │        │
                         YES│        │NO
                           ↓        │
                     grep_search    │
                           │        │
                           ↓        ↓
                  ┌─────────────────────────┐
                  │ CODE STRUCTURE query?   │
                  │ (inheritance, nesting)  │
                  └────────┬────────┬───────┘
                           │        │
                         YES│        │NO
                           ↓        │
                    ast_grep_search │
                           │        │
                           ↓        ↓
                  ┌─────────────────────────┐
                  │ BEHAVIORAL/CONCEPTUAL?  │
                  │ ("how", "where is",     │
                  │ "logic", "patterns")    │
                  └────────┬────────┬───────┘
                           │        │
                         YES│        │NO
                           ↓        │
                   semantic_search  │
                           │        │
                           ↓        ↓
                  ┌─────────────────────────┐
                  │ COMPILER-LEVEL NEED?    │
                  │ (definitions,           │
                  │ references)             │
                  └────────┬────────┬───────┘
                           │        │
                         YES│        │NO
                           ↓        │
                     lsp_*_tools    │
                           │        │
                           ↓        ↓
                        ┌─────┐  ┌──────────┐
                        │Done │  │fallback: │
                        └─────┘  │grep_search
                                 └──────────┘
```

---

## Flow 3: Delegation Decision Matrix

```
REQUEST TYPE                    ORCHESTRATOR    SPECIALISTS        EXECUTION
────────────────────────────────────────────────────────────────────────────

"Find X"                        Classify        └─ explore (async)  Parallel
                                               └─ return results    Immediate

"Research X"                    Classify        └─ dewey (async)     Parallel
                                               └─ return results    Immediate

"Review code"                   Classify        └─ code-reviewer     Parallel
                                               (async)              Immediate

"Fix bug" (attempt #1)          ATTEMPT FIX     (none)              Blocking
                                └─ fails        ↓

"Fix bug" (attempt #2)          ATTEMPT FIX     (none)              Blocking
                                └─ fails        ↓

"Fix bug" (attempt #3+)         BLOCK tools     └─ debugger         Blocking
                                via hook        (blocking)          Wait

"Design UI"                     NEVER direct    └─ frontend         Blocking
                                execution       (blocking via       Wait
                                               Gemini 3 Pro High)

"Implement feature"             Plan in         ├─ explore (async)  Parallel
(complex multi-step)            TodoWrite       ├─ dewey (async)    Immediate
                                              ├─ frontend (block)  Wait for
                                              └─ code-reviewer     UI
                                                (async)

"Architecture decision"         ATTEMPT 1-2     (none)              Blocking
(after 3+ failures)             └─ fail        └─ delphi (block)    Wait
                                └─ BLOCK       (GPT-5.2 with
                                   tools       extended thinking)

"Trivial change"                EXECUTE         (none)              Native
(typo, single line)             directly                           Immediate
```

---

## Flow 4: Parallel Execution Pattern

```
┌──────────────────────────────────────────────────────┐
│ REQUEST: "Implement auth AND test coverage AND docs"│
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ TodoWrite([                │
        │   Implement auth,          │
        │   Add test coverage,       │
        │   Write documentation      │
        │ ])                         │
        └────────────┬───────────────┘
                     │
                     ↓
        ┌────────────────────────────────────────────┐
        │ SAME RESPONSE: Spawn all agents in parallel│
        │                                             │
        │ Task(                   Task(              │
        │   subagent_type=        subagent_type=    │
        │   "frontend",           "code-reviewer",  │
        │   prompt="Implement     prompt="Write     │
        │   auth UI..."           tests for auth..." │
        │ )                       )                  │
        │                                            │
        │                         Task(             │
        │                           subagent_type=  │
        │                           "dewey",        │
        │                           prompt="Doc     │
        │                           best practices" │
        │                         )                  │
        └─┬─────────────────────┬─────────────────┬─┘
          │                     │                 │
    ┌─────↓─────┐         ┌─────↓─────┐    ┌─────↓─────┐
    │  Frontend  │         │Code Review │    │  Dewey   │
    │  Agent     │         │  Agent    │    │ Agent    │
    │            │         │           │    │          │
    │Executing:  │         │Executing: │    │Executing:│
    │├ UI design │         │├ Tests    │    │├Gathering│
    │├ Layout    │         │├ Coverage │    │ docs    │
    │├ Forms     │         │├ Edge     │    │├Writing  │
    │└ Styles   │         ││ cases    │    │examples │
    └─┬──────────┘         └─┬────────┘    │└Examples│
      │                      │             │        │
      └──────────┬───────────┴─────────────┘        │
                 │                                   │
                 ↓                                   ↓
        ┌──────────────────────────────┐  ┌──────────────────┐
        │ All tasks complete            │  │  All tasks       │
        │ (or timeout after 300s)       │  │  complete        │
        └──────────┬───────────────────┘  └────────┬─────────┘
                   │                               │
                   └───────────────┬────────────────┘
                                   │
                                   ↓
                    ┌──────────────────────────────┐
                    │ ORCHESTRATOR SYNTHESIZES     │
                    │ ├─ Merge UI + backend logic  │
                    │ ├─ Integrate test suite      │
                    │ ├─ Add documentation         │
                    │ ├─ Run final checks          │
                    │ ├─ Mark todos complete       │
                    │ └─ Respond to user           │
                    └──────────────────────────────┘
```

---

## Flow 5: Hook Integration Points

```
HOOK INTEGRATION ARCHITECTURE
════════════════════════════════════════════════════════════

        USER PROMPT
             │
             ↓
    ┌─────────────────────┐
    │ UserPromptSubmit    │ ← HOOK 1: Context injection
    │ Hook (if wired)     │
    │ ├─ Inject rules     │
    │ ├─ Add context      │
    │ └─ Preprocess       │
    └──────────┬──────────┘
               │
               ↓
    ┌─────────────────────┐
    │ Claude Code         │
    │ Auto-delegates      │
    │ to stravinsky       │
    └──────────┬──────────┘
               │
               ↓
    ┌─────────────────────────────────┐
    │ STRAVINSKY ORCHESTRATOR         │
    │ Plans work, creates Task()      │
    │ calls for delegation            │
    └──────────┬──────────────────────┘
               │
               ↓
    ┌──────────────────────────────┐
    │ PreToolUse Hook              │ ← HOOK 2: Block/Allow
    │ (if wired)                   │
    │ ├─ Intercept Read/Grep/Bash │
    │ ├─ Check complexity         │
    │ ├─ Decision: Block or Allow │
    │ └─ If block: exit code 2    │
    └───┬──────────────────┬───────┘
        │                  │
      ALLOW              BLOCK
        │                  │
        ↓                  ↓
    ┌────────┐       ┌──────────────┐
    │Native  │       │Orchestrator  │
    │tool    │       │falls back to │
    │runs    │       │Task() call   │
    │directly│       │to specialist │
    └────┬───┘       └────┬─────────┘
         │                │
         │                ↓
         │         ┌────────────────┐
         │         │Specialist Agent│
         │         │executes task   │
         │         └────┬───────────┘
         │              │
         └──────┬───────┘
                │
                ↓
    ┌──────────────────────────┐
    │ PostToolUse Hook         │ ← HOOK 3: Result aggregation
    │ (if wired)               │
    │ ├─ Detect completion     │
    │ ├─ Log results           │
    │ ├─ Update state          │
    │ └─ Signal synthesis      │
    └──────────┬───────────────┘
               │
               ↓
    ┌──────────────────────────┐
    │ Orchestrator synthesizes │
    │ Final response           │
    └──────────────────────────┘


MISSING IMPLEMENTATION
══════════════════════════════════════════════════════════════
✅ Python hook modules: mcp_bridge/hooks/ (30+)
❌ Hook scripts: .claude/agents/hooks/*.sh (NOT CREATED)
❌ Hook registration: .claude/settings.json (NOT CREATED)

WHAT'S NEEDED TO ACTIVATE
═════════════════════════════════════════════════════════════
1. Create: .claude/agents/hooks/pre_tool_use.sh
   ├─ Bash script
   ├─ Read stdin JSON (tool name, args)
   ├─ Logic: detect complex searches
   └─ Return: {"decision": "block"} + exit 2 to block

2. Create: .claude/agents/hooks/post_tool_use.sh
   ├─ Bash script
   ├─ Read stdin JSON (tool name, result)
   ├─ Log completion
   └─ Pass through result

3. Create: .claude/settings.json (or update if exists)
   ├─ Register pre_tool_use.sh hook
   ├─ Register post_tool_use.sh hook
   └─ Set execution order

4. Update: .claude/agents/stravinsky.md
   ├─ Add prompt section: "When you see PreToolUse block..."
   ├─ "...delegate to specialist via Task() tool"
   └─ Reference complete guide in stravinsky.md
```

---

## Flow 6: Cost Tier Routing

```
REQUEST COMPLEXITY → DELEGATION ROUTING
════════════════════════════════════════════════════════════

    Trivial
    (typo, 1-line)
         │
         ├─ NO delegation
         └─ Cost: 1x Sonnet cost (direct execution)
                │
                ↓
    Simple
    (find specific thing)
         │
         ├─ Delegate to: explore (FREE async)
         └─ Cost: 0.25 Haiku + 0.075 Gemini Flash ≈ $0.001
                │
                ↓
    Medium
    (research + code)
         │
         ├─ Parallel delegates:
         │  ├─ dewey (CHEAP async)
         │  ├─ code-reviewer (CHEAP async)
         │  └─ frontend (MEDIUM blocking)
         └─ Cost: Variable, but cheap agents async
                │
                ↓
    Hard
    (debugging)
         │
         ├─ Attempt 1: Orchestrator
         ├─ Attempt 2: Orchestrator
         ├─ Attempt 3: Delegate to debugger (MEDIUM blocking)
         └─ Cost: 2x Sonnet attempts + debugger fee
                │
                ↓
    Architectural
    (after 3+ failures)
         │
         ├─ Delegate to: delphi (EXPENSIVE blocking)
         │  └─ Uses GPT-5.2 + extended thinking
         └─ Cost: High, but prevents infinite loops


TOTAL COST SAVINGS WITH HOOK ENFORCEMENT
═════════════════════════════════════════════════════════════
Without hooks:
  Every search = Sonnet directly
  Sonnet cost: ~$0.003 per 1K tokens
  → Expensive for simple tasks

With hooks:
  Simple searches = free explore agent (parallel)
  Sonnet only orchestrates
  Gemini Flash does actual work
  → 10x cheaper for search-heavy workflows

Example: "Find all auth, doc it, test it"
  Without hooks: Sonnet does all 3 (expensive)
  With hooks: Sonnet plans, explore/dewey/frontend execute (cheap)
  Savings: ~70% for typical workflows
```

---

## Flow 7: Agent Capability Matrix

```
WHAT EACH AGENT CAN DO
════════════════════════════════════════════════════════════

STRAVINSKY (Orchestrator)      EXPLORE (Code Search)
┌─────────────────────────┐    ┌─────────────────────────┐
│ Core Tools:             │    │ Optimized For:          │
│ ├─ Read files           │    │ ├─ grep_search          │
│ ├─ Edit/Write           │    │ ├─ ast_grep_search      │
│ ├─ Bash commands        │    │ ├─ glob_files           │
│ ├─ Glob patterns        │    │ ├─ lsp tools            │
│ ├─ Task delegation      │    │ ├─ semantic_search      │
│ ├─ TodoWrite            │    │ └─ invoke_gemini        │
│ └─ Agent management     │    │                         │
│                         │    │ Returns:                │
│ Thinking Budget: 32k    │    │ ├─ File paths           │
│                         │    │ ├─ Line numbers         │
│ Execution: Primary      │    │ ├─ Code snippets        │
│ Model: Sonnet 4.5       │    │ └─ Pattern analysis     │
│ Cost: Moderate          │    │                         │
│                         │    │ Model: Gemini 3 Flash   │
│ Blocked from:           │    │ Cost: FREE              │
│ └─ Doing work directly  │    │ Execution: Async        │
│    (delegates instead)  │    │ Model: Haiku wrapper    │
└─────────────────────────┘    └─────────────────────────┘

DEWEY (Research)                FRONTEND (UI/UX)
┌─────────────────────────┐    ┌─────────────────────────┐
│ Optimized For:          │    │ Optimized For:          │
│ ├─ WebSearch            │    │ ├─ UI component design  │
│ ├─ External docs        │    │ ├─ Styling              │
│ ├─ Library examples      │    │ ├─ Layout               │
│ ├─ Best practices       │    │ ├─ Animations           │
│ ├─ Official docs        │    │ ├─ Responsive design    │
│ └─ Integration patterns │    │ ├─ Accessibility        │
│                         │    │ └─ User experience      │
│ Returns:                │    │                         │
│ ├─ Documentation links  │    │ Returns:                │
│ ├─ Code examples        │    │ ├─ Component code       │
│ ├─ Best practices       │    │ ├─ Styling (CSS/Tailwind)
│ └─ Recommendations      │    │ ├─ Layout templates     │
│                         │    │ └─ UX patterns          │
│ Model: Gemini 3 Flash   │    │                         │
│ Cost: CHEAP             │    │ Model: Gemini 3 Pro High
│ Execution: Async        │    │ Cost: MEDIUM            │
│ Has: WebSearch access   │    │ Execution: BLOCKING     │
│                         │    │ (always for visual)     │
└─────────────────────────┘    └─────────────────────────┘

CODE-REVIEWER (Quality)          DEBUGGER (Root Cause)
┌─────────────────────────┐    ┌─────────────────────────┐
│ Optimized For:          │    │ Optimized For:          │
│ ├─ Security analysis    │    │ ├─ Error analysis       │
│ ├─ Code quality         │    │ ├─ Stack trace parsing  │
│ ├─ Best practices       │    │ ├─ Root cause finding   │
│ ├─ Anti-patterns        │    │ ├─ Fix strategy         │
│ ├─ Bug detection        │    │ ├─ Edge case discovery  │
│ └─ Test coverage        │    │ └─ Debugging guidance   │
│                         │    │                         │
│ Returns:                │    │ Returns:                │
│ ├─ Security issues      │    │ ├─ Root cause analysis  │
│ ├─ Quality metrics      │    │ ├─ Hypothesis list      │
│ ├─ Improvement ideas    │    │ ├─ Debugging steps      │
│ └─ Code examples        │    │ └─ Fix recommendations  │
│                         │    │                         │
│ Model: Gemini 3 Flash   │    │ Model: Claude Sonnet    │
│ Cost: CHEAP             │    │ Cost: MEDIUM            │
│ Execution: Async        │    │ Execution: BLOCKING     │
│                         │    │ (after 2+ failures)     │
└─────────────────────────┘    └─────────────────────────┘

DELPHI (Architecture)
┌─────────────────────────┐
│ Optimized For:          │
│ ├─ Architecture design  │
│ ├─ System design        │
│ ├─ Trade-off analysis   │
│ ├─ Technology selection │
│ ├─ Complex decisions    │
│ └─ Strategic advice     │
│                         │
│ Returns:                │
│ ├─ Architecture proposal│
│ ├─ Rationale/trade-offs │
│ ├─ Implementation plan  │
│ ├─ Risk assessment      │
│ └─ Alternatives analysis│
│                         │
│ Model: GPT-5.2          │
│ Cost: EXPENSIVE         │
│ Execution: BLOCKING     │
│ (after 3+ failures)     │
│ Has: Extended thinking  │
│ (reasoning_effort)      │
└─────────────────────────┘
```

---

## Flow 8: Token Cost Comparison

```
TYPICAL WORKFLOW: "Find auth code, test it, document it"
═════════════════════════════════════════════════════════════

WITHOUT HOOKS (All Sonnet):
────────────────────────────────────
Task 1 - Find auth:     5k tokens × $0.003 = $0.015  ←─ Expensive
Task 2 - Test code:     8k tokens × $0.003 = $0.024      (Sonnet)
Task 3 - Document:      4k tokens × $0.003 = $0.012
                        ────────────────────────────
Total:                  17k tokens = $0.051 per request


WITH HOOKS (Specialized delegation):
──────────────────────────────────────
Orchestrator plan:       2k tokens × $0.003 = $0.006  ← Cheap
Explore (find):          3k tokens × FREE   = $0.000  ← Free
Code-reviewer (test):    5k tokens × FREE   = $0.000  ← Free
Dewey (document):        6k tokens × CHEAP  = $0.001  ← Cheap
Orchestrator synthesis:  2k tokens × $0.003 = $0.006
                        ────────────────────────────
Total:                   18k tokens = $0.013 per request

SAVINGS: 75% cheaper (4x cost reduction)
ADDITIONAL BENEFIT: Parallel execution (faster response)
```

---

**These flows form the foundation of Stravinsky's architecture.**

Key takeaway: The system is **almost complete**, but needs **hook integration** to enforce the delegation patterns automatically.

Status: Ready for Phase 1 (Hook Integration) implementation.
