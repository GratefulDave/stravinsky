# Stravinsky Strategic Plan
## Executive Summary
Stravinsky v0.4.56 is a mature MCP bridge for Claude Code enabling multi-model orchestration, native subagent delegation, and semantic code search. The project has 80 Python modules, 24 test files, 47 MCP tools, and 9 specialized native agents. Recent work focused on tool_search optimization (85% token reduction) and manifest-based incremental indexing.
## Current State Analysis
### Architecture Strengths
1. **Hybrid Hook System**: Defense-in-depth architecture with native Claude hooks (PreToolUse, PostToolUse, UserPromptSubmit) and 17+ MCP internal hooks working across process boundaries
2. **Zero-Import-Weight Startup**: Sub-second initialization via aggressive lazy loading
3. **OAuth-First with API Fallback**: Automatic degradation from OAuth to API keys on rate limits (Tier 3 quotas)
4. **Native Subagent Architecture**: Uses Task tool for zero-overhead delegation to specialist agents (explore, dewey, frontend, delphi, code-reviewer, debugger)
5. **Multi-Model Routing**: Seamless access to Gemini 3 Flash/Pro, GPT-5.2, Claude Sonnet/Opus via MCP tools
6. **Semantic Code Search**: ChromaDB + Ollama embeddings with automatic file watching and manifest-based incremental indexing
7. **LSP Integration**: Persistent language servers with 35x speedup, code refactoring, and advanced navigation
### Recent Achievements (v0.4.41-0.4.56)
* Tool_search with defer_loading (85% token reduction)
* Manifest-based incremental indexing for semantic search
* Test suite stabilization and improved session isolation
* Repository-based naming for vector databases
* File watcher normalization across symlinks
### Current Metrics
* **Codebase**: 80 Python modules in mcp_bridge/
* **Test Coverage**: 24 test files
* **MCP Tools**: 47 (model invoke, agents, search, LSP, semantic, sessions, skills)
* **Native Agents**: 9 (stravinsky, research-lead, implementation-lead, explore, dewey, code-reviewer, debugger, frontend, delphi)
* **Native Hooks**: 11 (PreToolUse, PostToolUse, UserPromptSubmit, PreCompact)
* **MCP Hooks**: 17+ (5 tiers: post-tool-call, context, optimization, behavior, lifecycle)
* **Version**: 0.4.56 (release/v0.4.41 branch)
* **Python Support**: 3.11-3.13 (3.14+ not supported due to onnxruntime dependency)
## Key Architectural Insights
### 1. Native Subagent Pattern (CORRECT Architecture)
The project has successfully migrated to native Claude Code subagents using the Task tool:
* **Orchestrator**: stravinsky.md (Sonnet 4.5) auto-delegates complex tasks
* **Specialists**: explore.md (Gemini Flash), dewey.md (Gemini Flash), frontend.md (Gemini Pro High), delphi.md (GPT-5.2)
* **Claude-Native**: code-reviewer.md (Sonnet), debugger.md (Sonnet)
* **Zero CLI Overhead**: Task tool delegation replaces agent_spawn CLI spawning
* **Hook-Based Control**: PreToolUse hooks enforce delegation patterns
### 2. Defense-in-Depth Hook Architecture (NOT Duplication)
The hybrid native + MCP hook system is intentional and necessary:
* **Native Hooks**: Run as subprocesses, intercept BEFORE MCP call, hard boundaries (exit code 2)
* **MCP Hooks**: Run in-process within MCP server, orchestrate behavior, track state
* **Process Isolation**: Different lifecycle points in fundamentally different processes
* **Capability Separation**: Native blocks tool execution, MCP routes models/tracks tokens
* **Validated Pattern**: Matches Kubernetes admission webhooks, WAF + app-layer validation
### 3. Cost-Based Agent Routing (oh-my-opencode Pattern)
Agent classification optimizes cost vs quality:
* **Always Async (Free/Cheap)**: explore (free), dewey (cheap), code-reviewer (cheap)
* **Blocking (Medium)**: debugger (after 2+ failures), frontend (ALL visual changes)
* **Blocking (Expensive)**: delphi (after 3+ failures, architecture decisions)
* **Primary**: stravinsky orchestrator (32k extended thinking budget)
### 4. Parallel Delegation Enforcement Gap
Critical issue identified in ARCHITECTURE.md:
* **Problem**: Advisory hooks (exit code 0) don't enforce parallel agent spawning
* **Symptom**: Sequential execution despite TodoWrite with multiple pending tasks
* **Root Cause**: PostToolUse timing too late, LLM task continuation bias, configuration conflicts
* **Impact**: Defeats core value proposition (multi-model parallel orchestration)
* **Status**: Documented, solution proposed, not yet implemented
## Critical Issues & Gaps
### 1. Parallel Delegation Not Enforced (High Priority)
**Problem**: Despite parallel delegation reminders, Claude executes tasks sequentially.
**Evidence**: Zero agent_spawn calls in logs despite TodoWrite with 2+ pending todos.
**Root Causes**:
* Advisory hooks (exit code 0) vs enforcement (exit code 2)
* PostToolUse timing (too late to block behavior)
* LLM task continuation bias (defaults to sequential execution)
* Configuration conflict: slash command says "NEVER use Task", native subagent says "Use Task", hook says "Use Task"
**Proposed Solutions**:
1. **Phase 1 - Immediate**: Resolve Task vs agent_spawn documentation conflict, strengthen hook messaging
2. **Phase 2 - Short Term**: Add progress tracking, session state persistence, display statistics
3. **Phase 3 - Long Term**: Implement runtime validation (MCP hook blocks non-agent-spawn tools after TodoWrite), add opt-in enforcement flag
### 2. Head-of-Line Blocking (Performance)
**Problem**: When agent uses invoke_gemini, entire MCP stdio transport blocks until Gemini responds (2-30s).
**Impact**: Prevents other agents from using ANY MCP tool during model invocation.
**Solution**: Local model proxy (FastAPI) for direct API calls without MCP protocol overhead.
**Benefits**: True parallelism (20+ concurrent model calls), observability (trace IDs, circuit breakers).
### 3. Configuration Conflicts
**Locations**:
* `.claude/commands/stravinsky.md` (slash command): "NEVER use Task tool"
* `.claude/agents/stravinsky.md` (native subagent): "Use Task tool for delegation"
* `.claude/hooks/todo_delegation.py` (PostToolUse): "Spawn a Task agent"
**Resolution**: Standardize on Task tool (native subagent pattern), update slash command docs.
### 4. Hook Unification Opportunity
**Current**: Native and MCP hooks have different event models, duplicate logic.
**Proposed**: Unified event model (ToolCallEvent, HookPolicy) with adapters for both hook types.
**Benefits**: DRY principle, easier testing, shared policy definitions.
## Roadmap & Next Steps
### Phase 1: Configuration Clarity (Immediate - 2 days)
**Goal**: Eliminate configuration conflicts preventing parallel delegation.
**Tasks**:
1. Update `.claude/commands/stravinsky.md` to remove "NEVER use Task" warning
2. Standardize on Task tool for native subagent delegation
3. Update `todo_delegation.py` hook messaging for consistency
4. Add prominent examples of CORRECT vs WRONG parallel delegation patterns
5. Document agent cost classification in YAML frontmatter
**Success Criteria**:
* Single source of truth for delegation pattern
* No conflicting instructions across slash commands, agents, hooks
* Clear documentation of when to use Task vs agent_spawn (legacy)
### Phase 2: Soft Parallel Enforcement (Short Term - 1 week)
**Goal**: Increase parallel delegation rate from ~30% to >60% without hard blocking.
**Tasks**:
1. Add session state tracking to `todo_delegation.py`
    * Track TodoWrite timestamp and pending count
    * Track agent_spawn/Task calls in same session
    * Display warning on next TodoWrite if no delegation occurred
2. Implement progress tracking dashboard
    * Show parallel delegation rate per session
    * Display statistics at session end
3. Enhance hook messaging with ASCII art borders, ALL CAPS for critical sections
4. Add line number references to agent configs in hook output
**Success Criteria**:
* Parallel delegation rate increases to >60%
* Agent spawn count correlates with TodoWrite pending count
* Logs show Task/agent_spawn calls after TodoWrite
* Non-blocking but visible accountability
### Phase 3: Hook Unification Layer (Medium Term - 2 weeks)
**Goal**: Reduce duplication between native and MCP hooks with unified interface.
**Tasks**:
1. Implement `mcp_bridge/hooks/events.py`
    * Canonical ToolCallEvent dataclass
    * Adapters: from_native_hook(), from_mcp_hook()
    * HookPolicy class with should_block, transform_result callbacks
2. Migrate 3 policies to unified interface
    * Truncation policy (native + MCP)
    * Delegation reminder policy (native + MCP)
    * Edit recovery policy (native + MCP)
3. Add policy testing framework
    * Unit tests for pure policy functions
    * Integration tests for adapter layer
**Success Criteria**:
* 3+ policies using unified HookPolicy class
* Native and MCP hooks share policy definitions (DRY)
* Test coverage >80% for hook policies
* Documentation updated with unified hook architecture
### Phase 4: Model Proxy (Critical Optimization - 2 weeks)
**Goal**: Eliminate head-of-line blocking for true parallel model invocation.
**Tasks**:
1. Implement `mcp_bridge/proxy/model_server.py`
    * FastAPI server on localhost:8765
    * Endpoints: /v1/gemini/generate, /v1/openai/chat
    * Direct API calls using OAuth tokens from Stravinsky
2. Add observability layer
    * Trace IDs for all requests
    * Circuit breaker on API failures
    * Rate limiting per model/provider
    * Metrics: latency, success rate, token usage
3. Migrate invoke_gemini/invoke_openai to use proxy
    * Optional: Fallback to MCP transport if proxy unavailable
    * Environment variable: STRAVINSKY_USE_PROXY=true/false
4. Benchmark parallel execution
    * Measure: 1 concurrent, 5 concurrent, 20 concurrent model calls
    * Compare: MCP transport vs model proxy
    * Target: <100ms overhead vs direct API calls
**Success Criteria**:
* 20+ concurrent model calls without blocking
* <100ms proxy overhead vs direct API calls
* Circuit breaker triggers and recovers correctly
* Trace IDs visible in all logs
* Zero MCP stdio blocking during model invocation
### Phase 5: Hard Parallel Enforcement (Long Term - 2 weeks)
**Goal**: Make parallel delegation the default, enforced pattern (opt-in).
**Tasks**:
1. Implement runtime validation (Solution 2 from ARCHITECTURE.md)
    * MCP hook: post_tool/parallel_validation.py (tracks TodoWrite)
    * MCP hook: pre_tool/agent_spawn_validator.py (blocks if no delegation)
    * Session state: require_agent_spawn flag
2. Add configuration option
    * `.stravinsky/config.json`: "enforce_parallel_delegation": true/false
    * Default: false (backward compatible, advisory only)
    * Users opt-in to strict enforcement
3. Implement override mechanism
    * TodoWrite parameter: {"parallel": false} for legitimate sequential work
    * Environment variable: STRAVINSKY_ALLOW_SEQUENTIAL=true
4. Add comprehensive testing
    * Test: 3 pending todos → must spawn 3 agents
    * Test: 1 pending todo → no enforcement
    * Test: 2 dependent + 1 independent → spawn 1 agent
    * Test: Override flag → allow sequential work
**Success Criteria**:
* Parallel delegation rate >80% when enforcement enabled
* Clear error messages explaining violations
* Override mechanism works for edge cases
* User feedback: "Stravinsky feels more automated"
* Backward compatible (opt-in enforcement)
### Phase 6: Documentation & Polish (Maintenance - 1 week)
**Goal**: Update all documentation with latest architecture, deprecate legacy patterns.
**Tasks**:
1. Update README.md
    * Emphasize native subagent pattern
    * Document agent cost classification
    * Add parallel delegation examples
2. Update WARP.md rules
    * Remove agent_spawn references (legacy)
    * Emphasize Task tool for delegation
    * Document enforcement configuration
3. Update docs/AGENTS.md
    * Add thinking_budget to agent YAML examples
    * Document cost/execution metadata
    * Add delegation decision tree
4. Create migration guide
    * For users coming from slash commands
    * For users with custom hooks
    * Tested with 3+ beta users
5. Mark slash commands as deprecated
    * Add deprecation warnings to `/stravinsky`, `/delphi`, `/dewey`
    * Redirect users to native subagent pattern
**Success Criteria**:
* All docs reference native subagent pattern as primary
* Slash commands clearly marked as deprecated
* Migration guide tested with 3+ users
* Zero documentation conflicts
* ARCHITECTURE.md updated with final state
## Optional Future Enhancements
### 1. Extended Thinking Budget Integration
**Status**: Documented in HOOKS.md but not yet implemented.
**Implementation**:
* Add `thinking_budget: 32000` to stravinsky.md and delphi.md YAML frontmatter
* For GPT models: Use `reasoning_effort: "medium"` in invoke_openai
* For Claude models: Already supported via native extended thinking
**Benefits**: Improves accuracy for complex orchestration and architecture decisions.
### 2. Agent Session Isolation
**Status**: Partially implemented (test fixes in v0.4.49).
**Remaining Work**: Ensure agents can't access each other's session state, prevent cross-contamination.
### 3. Semantic Search Enhancements
**Current**: ChromaDB + Ollama embeddings, file watcher, manifest-based indexing.
**Enhancements**:
* Hybrid search (semantic + BM25 keyword)
* Multi-query search (query expansion)
* Decomposed search (subtask parallelization)
* Enhanced search with reranking
**Status**: Tools exist (hybrid_search, multi_query_search, decomposed_search, enhanced_search) but need documentation and testing.
### 4. Visual Tool Output
**Idea**: Add structured output formats for complex tool results (JSON, tables, graphs).
**Use Case**: LSP diagnostics, semantic search results, agent progress tracking.
**Implementation**: PostToolUse hook transforms text results into rich formats.
### 5. Agent Cost Dashboard
**Idea**: Real-time tracking of token usage and cost per agent/session.
**Implementation**: MCP hook collects metrics, FastAPI endpoint serves dashboard.
**Display**: Terminal UI (rich), web dashboard (FastAPI + HTML).
## Testing & Validation Strategy
### Current Test Coverage
* **Test Files**: 24
* **Coverage**: Partial (auth, tools, hooks, LSP)
* **Gaps**: Native subagent workflows, parallel delegation enforcement
### Testing Priorities
1. **Parallel Delegation**: Test suite for TodoWrite → agent_spawn/Task patterns
2. **Hook Policies**: Unit tests for unified HookPolicy implementations
3. **Model Proxy**: Load testing for concurrent model invocations
4. **Session Isolation**: Ensure agents can't access each other's state
5. **Integration**: End-to-end workflows (research → plan → implement → review)
## Success Metrics
### Phase 1-2 (Configuration + Soft Enforcement)
* Parallel delegation rate: 30% → 60%
* Zero documentation conflicts
* User feedback: "Instructions are clearer"
### Phase 3-4 (Hook Unification + Model Proxy)
* Hook policy test coverage: >80%
* Concurrent model calls: 1 → 20+ without blocking
* Proxy overhead: <100ms
### Phase 5-6 (Hard Enforcement + Documentation)
* Parallel delegation rate: 60% → 80% (with enforcement enabled)
* Migration guide tested with 3+ users
* User feedback: "Stravinsky feels more automated"
## Open Questions
1. **Should enforcement apply to native subagents only or all contexts?**
    * Proposal: Enforce for native subagents (orchestrators), advisory for main conversation
2. **How to detect dependent vs independent todos?**
    * Conservative default: Assume all pending todos are independent
    * Future: User annotation ({"independent": true})
3. **Should Task tool support run_in_background parameter?**
    * Current: Task is synchronous (blocks until complete)
    * Future: May need async Task support in Claude Code
4. **What about non-delegation workflows?**
    * Need escape hatch: TodoWrite([..., {"parallel": false}])
    * Environment variable: STRAVINSKY_ALLOW_SEQUENTIAL=true
5. **Should model proxy be mandatory or optional?**
    * Proposal: Optional with STRAVINSKY_USE_PROXY=true/false
    * Default: false (backward compatible)
    * Auto-enable if >5 concurrent agents detected
## Risk Assessment
### Low Risk
* Configuration cleanup (Phase 1)
* Documentation updates (Phase 6)
* Hook messaging improvements (Phase 2)
### Medium Risk
* Hook unification layer (Phase 3) - requires careful abstraction design
* Soft enforcement (Phase 2) - must avoid being annoying to users
### High Risk
* Model proxy (Phase 4) - adds new failure mode (proxy unavailable)
* Hard enforcement (Phase 5) - may block legitimate sequential workflows
* Breaking changes to native subagent configs
### Mitigation Strategies
* **Model Proxy**: Fallback to MCP transport if proxy fails
* **Hard Enforcement**: Opt-in flag, backward compatible
* **Hook Changes**: Extensive testing, gradual rollout
* **Version Pinning**: Use @latest in installation to ensure updates propagate
## Conclusion
Stravinsky v0.4.56 is a mature, well-architected MCP bridge with strong fundamentals. The primary gap is parallel delegation enforcement, which can be addressed through a phased approach from configuration cleanup to hard enforcement. The hybrid hook architecture is correct and should be preserved. The model proxy is the critical optimization for true parallel model invocation. Focus on Phases 1-2 first for immediate impact, then Phases 3-4 for performance, and finally Phase 5 for automated orchestration.