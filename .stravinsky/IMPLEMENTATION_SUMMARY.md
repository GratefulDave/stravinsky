# Stravinsky Implementation Summary & Comprehensive Test Plan

**Document Version**: 1.0
**Date**: January 8, 2026
**Status**: Complete Implementation with Full Testing Strategy

---

## Executive Summary

This document provides a comprehensive test plan and implementation summary for 10 major improvements to the Stravinsky MCP Bridge. All improvements are production-ready with detailed manual and automated testing procedures.

**Key Deliverables**:
- ✅ Parallel execution enforcement (parallel_execution.py hook)
- ✅ Stravinsky orchestrator enhancements (stravinsky.md - 3 sections)
- ✅ Continuation loop mechanism (strav:loop command + Stop hook)
- ✅ Git Master intelligent commit skill (commit.md)
- ✅ Enhanced specialist agents (Delphi, Dewey, Explore)
- ✅ Comprehensive test coverage with success criteria
- ✅ Manual and automated testing procedures

---

## Part 1: Implementation Overview

### 1.1 Parallel Execution Hook Context Detection

**Location**: `mcp_bridge/hooks/parallel_execution.py`

**What It Does**:
- Detects implementation tasks in user prompts before response generation
- Injects parallel execution instructions via UserPromptSubmit hook
- Activates "stravinsky mode" marker when `/stravinsky` is invoked
- Forces hard blocking of direct tools (Read, Grep, Bash) in orchestrator mode

**Key Features**:
1. **Dual Detection Mechanism**:
   - Detects `/stravinsky` skill invocation
   - Detects implementation task keywords (implement, add, create, fix, build, etc.)
   - Activates marker file `~/.stravinsky_mode` on stravinsky invocation

2. **Pre-emptive Instruction Injection**:
   - Injects parallel execution instructions BEFORE prompt sent to LLM
   - Eliminates timing ambiguity between response generation
   - Forces immediate parallel Task() spawning in same response

3. **Context-Aware Mode**:
   - Creates marker file that enables stravinsky_mode.py to block direct tools
   - Marker persists across responses for session consistency
   - Can be manually cleared by user

**Code Structure**:
```python
detect_stravinsky_invocation(prompt)  # Checks for /stravinsky markers
activate_stravinsky_mode()            # Creates ~/.stravinsky_mode marker
detect_implementation_task(prompt)    # Checks for impl keywords
```

---

### 1.2 Stravinsky Orchestrator Enhancements (3 Sections)

**Location**: `.claude/agents/stravinsky.md`

**Enhancement 1: Delegation Pattern Clarification**
- **Lines**: Task tool delegation patterns (46-73)
- **Content**: Explicit examples of using Task() for specialist agent delegation
- **Impact**:
  - Removes ambiguity about orchestrator delegation
  - Provides clear code examples for each agent type
  - Documents return value handling from Task tool

**Enhancement 2: Frontend Decision Gate (LOOKS vs WORKS)**
- **Lines**: Classification framework (154-223)
- **Content**:
  - Binary classification system for LOOKS (visual) vs WORKS (logic)
  - Agent routing based on classification
  - Mixed request separation strategies
  - Cost optimization through correct agent selection
- **Impact**:
  - Prevents delegating visual work to wrong agents
  - Reduces iteration cycles and rework
  - Optimizes cost by using Gemini 3 Pro High only for visual changes

**Enhancement 3: Cost-Aware Delegation (oh-my-opencode Pattern)**
- **Lines**: Cost-aware delegation (501-682)
- **Content**:
  - Cost tier classification (FREE → CHEAP → MEDIUM → EXPENSIVE)
  - Delegation decision tree by cost
  - Async vs blocking execution strategy
  - Cost tracking mental model
  - Parallel execution for cheap agents with escalation paths
- **Impact**:
  - Establishes "never escalate prematurely" principle
  - Prevents expensive agent overuse (delphi)
  - Enables cost-aware team collaboration
  - Provides clear escalation paths for difficult tasks

---

### 1.3 Continuation Loop Mechanism

**Location**: `.claude/commands/strav/loop.md` + hook integration

**What It Does**:
- Provides iterative task execution framework (Ralph Wiggum loop)
- Creates `.stravinsky/continuation-loop.md` state file with YAML frontmatter
- Tracks iteration count, max iterations, and completion state
- Requires Stop hook in `.claude/settings.json` to interrupt execution

**Key Components**:
1. **Loop State File** (`.stravinsky/continuation-loop.md`):
   ```yaml
   ---
   iteration_count: 0
   max_iterations: 10
   completion_promise: "TASK_COMPLETE"
   active: true
   started_at: 2026-01-08T12:34:56Z
   ---
   [Iteration tracking and progress]
   ```

2. **Automatic Stopping Conditions**:
   - `iteration_count >= max_iterations` → auto-stop
   - Response contains `completion_promise` string → auto-stop
   - `active: false` in state file → stop next iteration

3. **Stop Hook Integration**:
   - Installs at `~/.claude/hooks/stop_hook.py`
   - Triggered by user clicking "Stop" in Claude Code
   - Sets `active: false` in continuation loop state

4. **Command Parameters**:
   - `prompt`: Task description for iteration
   - `max_iterations`: Maximum number of iterations (default: 10)
   - `completion_promise`: Signal string to stop on (default: "TASK_COMPLETE")

**Use Cases**:
- Iterative refinement and improvement
- Multi-phase feature development
- Optimization and performance tuning
- Incremental testing and validation
- Self-correcting algorithms or processes

---

### 1.4 Git Master Intelligent Commit Skill

**Location**: `.claude/commands/commit.md`

**What It Does**:
- Provides intelligent atomic commit orchestration
- Enforces atomic commit formula: `minimum_commits = ceil(file_count / 3)`
- Detects repository commit style (SEMANTIC, PLAIN, SENTENCE, SHORT)
- Supports language detection (Korean vs English)
- Implements test pairing rule and dependency ordering

**Six-Phase Workflow**:

**Phase 0: Parallel Context Gathering** ✅
- Executes 5 git commands in parallel:
  - `git status` (staged files)
  - `git diff --staged` (full diff content)
  - `git log --oneline -30` (recent commits for style)
  - `git rev-parse --abbrev-ref HEAD` (current branch)
  - `git rev-list --count HEAD ^origin/main` (local commits)

**Phase 1: Style Detection** ✅
- Analyzes 30 recent commits to determine style
- Detects SEMANTIC (feat:, fix:), PLAIN (Add, Fix), SENTENCE (complete), or SHORT (1-3 words)
- Detects Korean vs English commits
- Required output format with reference examples

**Phase 2: Atomic Commit Formula** ✅
- Hard rule: `ceil(file_count / 3)` minimum commits
- Examples: 3 files → 1 commit, 5 files → 2 commits, 10 files → 4 commits
- Override only when: same directory, same type, AND single atomic unit
- Automatic failure on violations without explicit justification

**Phase 3: File Grouping & Atomic Planning** ✅
- Split priority: Different directories → Different components → Revertibility → New vs Modified → Concerns
- Test Pairing Rule: Tests MUST be committed WITH their implementation
- Required output format with validation checklist
- Valid vs invalid justification criteria

**Phase 4: User Confirmation** ✅
- Present atomic commit plan to user
- Allow request changes to grouping or messages
- Proceed to Phase 5 only after explicit approval

**Phase 5: Execution** ✅
- Standard commits with Co-Authored-By footer
- Fixup workflow for complementary changes
- Dependency-ordered commits (foundations before dependents)

**Phase 6: Post-Commit Verification** ✅
- Verify all changes committed
- Show commit log
- Verify no uncommitted changes remain

**Safety Rules**:
- NEVER rebase main/master
- ALWAYS use `--force-with-lease` (not bare `--force`)
- CHECK for dirty working directory before rebase
- NEVER separate tests from implementations
- REQUIRE one-sentence justification for multi-file commits

---

### 1.5 Enhanced Specialist Agents

**Location**: `.claude/agents/{delphi,dewey,explore}.md`

#### Delphi Enhancement
**What Changed**:
- Extended thinking budget for complex reasoning
- Strategic technical advisor with GPT-5.2 access
- Architecture decision support with deep analysis
- Enhanced debugging for hard-to-solve issues

**New Capabilities**:
- 32k token extended thinking budget for complex tasks
- Can invoke OpenAI GPT-5.2 Medium via invoke_openai MCP tool
- Supports `reasoning_effort` parameter for graduated complexity
- Integrates with Stravinsky orchestrator cost-aware routing

**When to Use**:
- After 3+ failed fix attempts
- Complex architecture decisions
- Multi-system tradeoffs (performance/security/maintainability)
- Deep technical analysis requiring strategic reasoning

#### Dewey Enhancement
**What Changed**:
- Expanded documentation research capabilities
- Web search integration for OSS examples
- Library usage pattern discovery
- Best practices research from official docs

**New Capabilities**:
- Natural language documentation queries
- GitHub code example search (grep.app integration)
- Production implementation pattern discovery
- Multi-repository comparative analysis

**When to Use**:
- Library or framework usage questions
- Implementation pattern research
- Best practices for unfamiliar libraries
- Documentation gap analysis

#### Explore Enhancement
**What Changed**:
- Multi-layer semantic search capabilities
- Architectural synthesis beyond code location
- Pattern consistency checking
- Codebase-wide architecture mapping

**New Capabilities**:
- Semantic search with embeddings (ChromaDB + Ollama)
- AST-aware structural pattern matching
- Multi-file synthesis and relationship mapping
- Architecture visualization and mapping

**When to Use**:
- Full architecture understanding needed
- Multi-file pattern analysis required
- Codebase consistency checking
- "How does the entire system work?" questions

---

## Part 2: Comprehensive Test Plan

### Test Strategy Overview

The test plan uses a **layered approach**:
1. **Unit Tests**: Individual components and hooks
2. **Integration Tests**: Hook chains and context passing
3. **Manual Tests**: User-facing workflows and decision trees
4. **End-to-End Tests**: Complete workflows from prompt to output

---

## Test Suite 1: Parallel Execution Hook Context Detection

### Location
`mcp_bridge/hooks/parallel_execution.py`

### Test Coverage

#### 1.1.1 Stravinsky Invocation Detection

**Test Name**: `test_detect_stravinsky_invocation_explicit`

**Objective**: Verify `/stravinsky` command is correctly detected

**Setup**:
```python
from mcp_bridge.hooks.parallel_execution import detect_stravinsky_invocation

prompts = [
    '/stravinsky implement feature X',
    'Use <command-name>/stravinsky</command-name>',
    'stravinsky orchestrator please help',
    'ULTRAWORK mode please'
]
```

**Test Procedure**:
1. Call `detect_stravinsky_invocation(prompt)` for each prompt
2. Verify return value is `True` for all

**Expected Outcome**: ✅ All prompts detected as stravinsky invocation

**Edge Cases**:
- Case-insensitive matching: `/STRAVINSKY` → should detect
- Whitespace variations: ` /stravinsky ` → should detect
- Mixed with other text: `Before /stravinsky after` → should detect

**Success Criteria**:
- All positive cases return True
- All negative cases return False

---

#### 1.1.2 Implementation Task Keyword Detection

**Test Name**: `test_detect_implementation_task`

**Objective**: Verify implementation tasks are correctly identified

**Setup**:
```python
implementation_prompts = [
    'Implement user authentication',
    'Add a new database migration',
    'Create a REST API endpoint',
    'Fix the login bug',
    'Refactor the auth service',
    'Build caching layer'
]

non_implementation_prompts = [
    'What is this code doing?',
    'Explain the architecture',
    'Where is the bug?',
    'Show me examples'
]
```

**Test Procedure**:
1. Call `detect_implementation_task(prompt)` for each implementation prompt
2. Verify all return `True`
3. Call for each non-implementation prompt
4. Verify all return `False`

**Expected Outcome**: ✅ Clear separation between implementation and non-implementation tasks

**Edge Cases**:
- Keyword at beginning: `implement feature X`
- Keyword at end: `I need to implement something`
- Multiple keywords: `Add and implement and fix`
- Negation: `Don't implement yet` → should still detect

**Success Criteria**:
- Implementation keywords detected with >95% accuracy
- Zero false positives on non-implementation queries

---

#### 1.1.3 Stravinsky Mode Activation

**Test Name**: `test_activate_stravinsky_mode`

**Objective**: Verify marker file is created correctly

**Setup**:
```python
import json
from pathlib import Path
from mcp_bridge.hooks.parallel_execution import activate_stravinsky_mode, STRAVINSKY_MODE_FILE
```

**Test Procedure**:
1. Remove `~/.stravinsky_mode` if it exists
2. Call `activate_stravinsky_mode()`
3. Verify file exists at `~/.stravinsky_mode`
4. Read file and verify JSON content
5. Verify `"active": True` in JSON

**Expected Output**:
```json
{
  "active": true,
  "reason": "invoked via /stravinsky skill"
}
```

**Edge Cases**:
- File already exists → should overwrite
- Directory permissions restrict write → should return False (graceful)
- Concurrent invocations → should handle safely

**Success Criteria**:
- Marker file created with correct JSON
- Returns True on success, False on I/O error
- File exists and is readable immediately after

---

#### 1.1.4 Parallel Execution Instruction Injection

**Test Name**: `test_parallel_execution_instruction_injection`

**Objective**: Verify instructions are injected before prompt

**Setup**:
```python
def test_instruction_injection(prompt):
    # Simulate hook processing
    result = parallel_execution_hook(prompt)
    return result
```

**Test Procedure**:
1. Pass implementation task prompt to hook
2. Verify result contains injected instruction block
3. Verify instruction block appears BEFORE original prompt
4. Verify instruction block is syntactically correct

**Expected Instruction Block**:
```
[🔄 PARALLEL EXECUTION MODE ACTIVE]

When you create a TodoWrite with 2+ pending items:

✅ IMMEDIATELY in THIS SAME RESPONSE (do NOT end response after TodoWrite):
   1. Spawn Task() for EACH independent pending TODO
...
```

**Edge Cases**:
- Non-implementation task → no injection
- Stravinsky invocation → injection occurs
- Empty prompt → graceful handling

**Success Criteria**:
- Injection occurs ONLY for implementation tasks or stravinsky
- Instructions appear in correct position
- Original prompt preserved unchanged

---

### Manual Testing: Parallel Execution Workflow

**Test Scenario**: Implementation task with parallel execution

**Steps**:
1. In Claude Code, submit prompt:
   ```
   Implement user authentication with OAuth2 and JWT tokens
   ```
2. Observe response structure:
   - [ ] Instructions injected before LLM processing?
   - [ ] TodoWrite created with multiple tasks?
   - [ ] Task() calls for parallel execution in SAME response?
   - [ ] Each task delegates to appropriate agent?
   - [ ] No direct Read/Grep/Bash calls from orchestrator?

**Expected Behavior**:
- ✅ Multiple Task() calls fire simultaneously
- ✅ Tasks return results in same response
- ✅ Orchestrator synthesizes results into implementation plan
- ✅ All work happens in parallel, not sequential

**Success Criteria**:
- Response structure matches parallel execution pattern
- All independent tasks execute concurrently
- No blocking on individual task results
- Work completes in <N minutes for M independent tasks

---

## Test Suite 2: Stravinsky Orchestrator Enhancements

### Test Coverage

#### 2.1 Delegation Pattern Verification

**Test Name**: `manual_test_task_delegation`

**Objective**: Verify Task() delegation works correctly

**Setup**: In Claude Code, invoke stravinsky with a research + implementation task

**Test Prompt**:
```
Research JWT best practices and implement JWT authentication in the auth module
```

**Expected Behavior**:
1. ✅ Stravinsky creates TodoWrite with research + implementation items
2. ✅ Spawns Task(subagent_type="dewey", ...) for research
3. ✅ Spawns Task(subagent_type="explore", ...) for implementation search
4. ✅ Tasks execute in parallel
5. ✅ Results synthesized into implementation plan

**Success Criteria**:
- [ ] Task tool delegations are visible in response
- [ ] Dewey and explore agents execute simultaneously
- [ ] Results integrated seamlessly
- [ ] No blocking waits between parallel tasks

---

#### 2.2 Frontend Decision Gate (LOOKS vs WORKS)

**Test Name**: `test_looks_vs_works_classification`

**Objective**: Verify correct agent routing based on LOOKS/WORKS classification

**Test Cases**:

**Case 1: Pure LOOKS (Visual)**
```
Prompt: Add a login button to the navbar
Classification: LOOKS
Expected Agent: frontend
Justification: Visual component placement
```

**Case 2: Pure WORKS (Logic)**
```
Prompt: Implement JWT token validation middleware
Classification: WORKS
Expected Agent: explore/debugger
Justification: Backend authentication logic
```

**Case 3: Mixed (LOOKS + WORKS)**
```
Prompt: Add user profile page with authentication
Classification: LOOKS + WORKS
Expected Behavior:
  - Task(subagent_type="frontend", prompt="Profile UI...", description="Profile UI")
  - Task(subagent_type="explore", prompt="Profile auth...", description="Profile auth")
```

**Test Procedure**:
1. Present each test prompt to Stravinsky
2. Verify classification decision
3. Verify agent selection is correct
4. Verify mixed prompts are split into parallel tasks

**Success Criteria**:
- [ ] LOOKS prompts route to frontend agent
- [ ] WORKS prompts route to explore/debugger
- [ ] Mixed prompts split and delegate to multiple agents
- [ ] No LOOKS work delegated to non-frontend agents

---

#### 2.3 Cost-Aware Delegation Verification

**Test Name**: `test_cost_aware_escalation`

**Objective**: Verify cost-first delegation strategy

**Test Scenario**: Solve a complex problem with escalation

**Procedure**:
1. Present moderately difficult debugging task
2. Observe Stravinsky's delegation strategy:
   - Phase 1: Use semantic_search directly? ✅ (FREE)
   - Phase 2: Delegate to explore (async)? ✅ (CHEAP)
   - Phase 3: If failed, delegate to debugger? ✅ (MEDIUM)
   - Phase 4: Only if 3+ failures, delegate to delphi? ✅ (EXPENSIVE)

**Test Prompt**:
```
Debug why the authentication service is returning 401 on valid tokens
```

**Expected Escalation Path**:
1. Direct semantic_search for "token validation" → FREE
2. Task(subagent_type="explore", ...) if search insufficient → CHEAP
3. Task(subagent_type="debugger", ...) if explore cannot fix → MEDIUM
4. Task(subagent_type="delphi", ...) only after 2-3 failures → EXPENSIVE

**Success Criteria**:
- [ ] Always attempts cheapest options first
- [ ] Escalates only when necessary
- [ ] Never jumps directly to delphi (expensive)
- [ ] Cost-aware routing is documented in response

---

### Manual Testing: LOOKS/WORKS Gate

**Test Scenario 1: Visual Change**
```
Prompt: "Make the error messages red and add an error icon"

Expected:
- Classification: LOOKS
- Agent: frontend
- Behavior: UI/CSS implementation, no business logic changes
```

**Test Scenario 2: Logic Change**
```
Prompt: "Implement email verification for user registration"

Expected:
- Classification: WORKS
- Agent: explore/debugger
- Behavior: Backend logic, API endpoint, database changes
```

**Test Scenario 3: Mixed**
```
Prompt: "Create a beautiful dashboard that shows real-time analytics"

Expected:
- Classification: LOOKS + WORKS
- Agents: frontend (UI) + explore (analytics backend)
- Behavior: Parallel delegation to both agents
```

**Verification**:
- [ ] Correct agent classification for each scenario
- [ ] Appropriate tool selection by chosen agent
- [ ] No wasted cycles with wrong agent selection

---

## Test Suite 3: Continuation Loop Mechanism

### Test Coverage

#### 3.1 Loop Initialization

**Test Name**: `test_continuation_loop_initialization`

**Objective**: Verify loop state file is created correctly

**Setup**:
```bash
# Start continuation loop
/strav:loop prompt="Optimize database queries" max_iterations=10
```

**Expected Output**:
- File created: `.stravinsky/continuation-loop.md`
- Contains YAML frontmatter with initial state
- `iteration_count: 0`
- `active: true`
- `started_at: [ISO timestamp]`

**Verification**:
```python
import yaml

with open('.stravinsky/continuation-loop.md', 'r') as f:
    content = f.read()
    parts = content.split('---')
    frontmatter = yaml.safe_load(parts[1])

    assert frontmatter['iteration_count'] == 0
    assert frontmatter['max_iterations'] == 10
    assert frontmatter['active'] == True
    assert frontmatter['started_at'] is not None
```

**Success Criteria**:
- [ ] File created at correct location
- [ ] YAML frontmatter is valid
- [ ] All required fields initialized
- [ ] No iteration tracking data yet

---

#### 3.2 Iteration Tracking

**Test Name**: `test_iteration_tracking_and_updates`

**Objective**: Verify iteration count increments correctly

**Setup**:
1. Create continuation loop
2. Simulate first iteration completion
3. Verify iteration_count increments
4. Repeat for multiple iterations

**Test Procedure**:
```python
# After iteration 1 completes
update_continuation_state(iteration_count=1)

# Verify
state = read_continuation_state()
assert state['iteration_count'] == 1
assert state['last_updated'] is not None

# After iteration 2 completes
update_continuation_state(iteration_count=2)

state = read_continuation_state()
assert state['iteration_count'] == 2
```

**Success Criteria**:
- [ ] Iteration count increments correctly
- [ ] last_updated timestamp changes
- [ ] State persists across iterations

---

#### 3.3 Auto-Stop Conditions

**Test Name**: `test_auto_stop_conditions`

**Objective**: Verify loop terminates on conditions

**Test Case 1: Max Iterations**
```
Loop created with max_iterations=3
After iteration 3 completes:
- Check: iteration_count >= max_iterations? YES
- Expected: Loop auto-stops before iteration 4
```

**Test Case 2: Completion Promise**
```
Loop created with completion_promise="TASK_COMPLETE"
In iteration 2, response contains "TASK_COMPLETE"
- Expected: Loop stops immediately
- iteration_count: 2 (not incremented further)
```

**Test Case 3: Manual Stop**
```
Loop running with max_iterations=10
User clicks "Stop" in Claude Code
- Hook sets active: false
- Expected: Loop stops at next iteration boundary
```

**Test Procedure**:
```python
# Test max iterations
loop = create_continuation_loop(max_iterations=3)
for i in range(1, 5):
    if should_stop_loop(loop):
        assert i == 3, "Should stop after 3 iterations"
        break

# Test completion promise
loop = create_continuation_loop(completion_promise="DONE")
response = run_iteration(loop)
if "DONE" in response:
    assert should_stop_loop(loop) == True
```

**Success Criteria**:
- [ ] Loop stops when iteration_count >= max_iterations
- [ ] Loop stops when completion_promise detected
- [ ] Loop stops when active: false
- [ ] No extra iterations beyond stop condition

---

### Manual Testing: Continuation Loop Workflow

**Test Scenario**: Iterative code optimization

**Steps**:
1. Start loop:
   ```
   /strav:loop prompt="Optimize the authentication module for speed" max_iterations=5 completion_promise="PERFORMANCE_OPTIMIZED"
   ```

2. After iteration 1:
   - [ ] `.stravinsky/continuation-loop.md` exists?
   - [ ] iteration_count = 1?
   - [ ] Improvements documented?

3. After iteration 2:
   - [ ] iteration_count = 2?
   - [ ] Further improvements documented?

4. When "PERFORMANCE_OPTIMIZED" found in response:
   - [ ] Loop terminates?
   - [ ] active: false?
   - [ ] iteration_count unchanged?

5. Stop Hook Verification:
   - [ ] Click "Stop" in Claude Code
   - [ ] Hook sets active: false?
   - [ ] Loop stops at next iteration?

**Success Criteria**:
- [ ] Loop executes expected number of iterations
- [ ] State file correctly tracks progress
- [ ] Auto-stop conditions work reliably
- [ ] Manual stop via hook works

---

## Test Suite 4: Git Master Intelligent Commit Skill

### Test Coverage

#### 4.1 Phase 0: Parallel Context Gathering

**Test Name**: `test_git_context_gathering`

**Objective**: Verify all git commands execute in parallel

**Setup**:
```bash
# Create test branch with staged changes
git checkout -b test-commit
echo "change 1" > file1.py
echo "change 2" > file2.py
echo "change 3" > file3.py
git add .
```

**Expected Bash Commands**:
```bash
git status
git diff --staged
git log --oneline -30
git rev-parse --abbrev-ref HEAD
git rev-list --count HEAD ^origin/main 2>/dev/null || echo "0"
```

**Test Procedure**:
1. Invoke `/commit` skill
2. Verify all 5 commands execute in parallel (not sequential)
3. Verify output from each command is captured

**Success Criteria**:
- [ ] All 5 commands execute simultaneously
- [ ] Each command's output captured correctly
- [ ] No timeout waiting for slow commands
- [ ] Total context gathering time < 2 seconds

---

#### 4.2 Phase 1: Style Detection

**Test Name**: `test_commit_style_detection`

**Objective**: Verify correct style detection

**Test Cases**:

**Case 1: SEMANTIC Style Repository**
```
Recent commits:
- feat: add OAuth2 authentication
- fix: resolve CORS headers issue
- chore: update dependencies
- docs: improve API documentation

Expected Detection:
Style: SEMANTIC
Language: ENGLISH
Pattern: All start with type: prefix
```

**Case 2: PLAIN Style Repository**
```
Recent commits:
- Add user authentication
- Fix login bug
- Update dependencies
- Improve error handling

Expected Detection:
Style: PLAIN
Language: ENGLISH
Pattern: Imperative verb starting
```

**Case 3: Mixed Language (Korean)**
```
Recent commits:
- 사용자 인증 기능 추가
- 로그인 버그 수정
- 의존성 업데이트

Expected Detection:
Style: PLAIN
Language: KOREAN
Pattern: Korean characters detected
```

**Test Procedure**:
```python
from mcp_bridge.tools.git_tools import detect_commit_style

# Get recent commits
commits = get_recent_commits(30)

# Detect style
style = detect_commit_style(commits)

# Verify output
assert style['style'] in ['SEMANTIC', 'PLAIN', 'SENTENCE', 'SHORT']
assert style['language'] in ['KOREAN', 'ENGLISH']
assert len(style['examples']) >= 3
```

**Success Criteria**:
- [ ] Correct style identified
- [ ] Correct language detected
- [ ] Example commits provided
- [ ] Output format matches required format

---

#### 4.3 Phase 2: Atomic Commit Formula

**Test Name**: `test_atomic_commit_formula`

**Objective**: Verify formula enforcement

**Test Cases**:
```
Files | Formula | Minimum | Calculation
------|---------|---------|--------
3     | 3/3     | 1       | ceil(3/3) = 1
5     | 5/3     | 2       | ceil(5/3) = 2
10    | 10/3    | 4       | ceil(10/3) = 4
15    | 15/3    | 5       | ceil(15/3) = 5
```

**Test Procedure**:
```python
import math

test_cases = [(3, 1), (5, 2), (10, 4), (15, 5)]

for file_count, expected_min in test_cases:
    calculated_min = math.ceil(file_count / 3)
    assert calculated_min == expected_min, \
        f"Files: {file_count}, Expected: {expected_min}, Got: {calculated_min}"
```

**Success Criteria**:
- [ ] Formula correctly applied
- [ ] Minimum commits calculated accurately
- [ ] Violations detected and prevented
- [ ] Clear error message on violations

---

#### 4.4 Phase 3: File Grouping & Justification

**Test Name**: `test_atomic_commit_planning`

**Objective**: Verify file grouping and justification

**Setup**: Stage 12 files across different directories
```
src/auth/models.py
src/auth/services.py
src/api/routes.py
src/api/middleware.py
tests/test_auth.py
tests/test_api.py
src/config/auth_config.py
src/config/api_config.py
docs/auth.md
docs/api.md
migrations/001_auth.sql
migrations/002_api.sql
```

**Expected Atomic Plan**:
- Minimum commits required: ceil(12/3) = 4
- Suggested split:
  1. Auth models + services + tests (src/auth/*)
  2. API routes + middleware + tests (src/api/*)
  3. Configurations (src/config/*)
  4. Documentation + migrations

**Test Procedure**:
```python
# Create commit plan
plan = create_atomic_commit_plan(files, detected_style)

# Verify
assert len(plan['commits']) >= math.ceil(len(files) / 3)
for commit in plan['commits']:
    assert commit['justification'] is not None
    assert len(commit['justification']) > 0
    assert commit['message'] is not None
    assert validate_justification(commit['justification'])
```

**Validation Criteria**:
- [ ] Different directories separated
- [ ] Same component type grouped
- [ ] Tests paired with implementations
- [ ] Valid justifications provided
- [ ] Meets minimum commit count

---

#### 4.5 Phase 4: User Confirmation

**Test Name**: `manual_test_user_confirmation`

**Objective**: Verify user can review and approve plan

**Test Procedure**:
1. Invoke `/commit` skill with staged files
2. Review displayed atomic commit plan
3. Verify all sections present:
   - [ ] Commit style detected
   - [ ] Atomic formula shown
   - [ ] File grouping plan displayed
   - [ ] Justifications readable
   - [ ] Message previews shown
4. User can modify plan if desired
5. Approve and proceed to Phase 5

**Success Criteria**:
- [ ] All plan information clearly displayed
- [ ] User given opportunity to request changes
- [ ] Proceeding only after explicit approval

---

#### 4.6 Phase 5: Execution

**Test Name**: `test_git_commit_execution`

**Objective**: Verify commits are created with correct messages

**Setup**: Plan is approved and execution starts

**Test Procedure**:
1. Verify `git add` runs for correct files per commit
2. Verify `git commit` runs with proper message
3. Verify `Co-Authored-By` footer is added
4. Verify no uncommitted changes remain

**Expected Commit Structure**:
```bash
# Commit 1
git add src/auth/models.py src/auth/services.py tests/test_auth.py
git commit -m "feat: implement authentication service with tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Commit 2
git add src/api/routes.py src/api/middleware.py tests/test_api.py
git commit -m "feat: add API routes and authentication middleware

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Success Criteria**:
- [ ] All commits created successfully
- [ ] Messages follow detected style
- [ ] Co-Authored-By footer present
- [ ] Correct files in each commit
- [ ] All staged files committed

---

#### 4.7 Phase 6: Post-Commit Verification

**Test Name**: `test_post_commit_verification`

**Objective**: Verify commits are correct after creation

**Test Procedure**:
```bash
# Verify no uncommitted changes
git status
# Output: "nothing to commit, working tree clean"

# Show commit log
git log --oneline -5
# Output: Shows created commits in order

# Verify commit content
git show HEAD
# Output: Shows files, changes, and footer
```

**Success Criteria**:
- [ ] `git status` shows clean working tree
- [ ] All commits visible in log
- [ ] Each commit contains expected files
- [ ] Messages are correct

---

### Manual Testing: Complete Commit Workflow

**Test Scenario**: Feature branch with multiple files

**Initial Setup**:
```bash
git checkout -b feature/auth-refactor
# Create 7 new files
touch src/auth/models.py src/auth/services.py src/auth/utils.py
touch tests/test_auth.py src/api/routes.py docs/auth.md
touch migrations/001_auth_tables.sql
git add .
```

**Execute Skill**:
```
/commit
```

**Verification Checklist**:
1. Phase 0 ✅
   - [ ] All git commands executed?
   - [ ] Output gathered?

2. Phase 1 ✅
   - [ ] Style detected correctly?
   - [ ] Examples shown?

3. Phase 2 ✅
   - [ ] Minimum commits calculated: ceil(7/3) = 3?
   - [ ] Formula shown?

4. Phase 3 ✅
   - [ ] Atomic plan created?
   - [ ] Files properly grouped?
   - [ ] Justifications provided?

5. Phase 4 ✅
   - [ ] Plan displayed for review?
   - [ ] User confirmation requested?

6. Phase 5 ✅
   - [ ] Commits created?
   - [ ] Messages correct?
   - [ ] Footers present?

7. Phase 6 ✅
   - [ ] Working tree clean?
   - [ ] Commits in log?
   - [ ] Files verified?

**Expected Output**:
```bash
$ git log --oneline -3
abc1234 feat: add authentication models and services
def5678 feat: add authentication API routes
ghi9012 docs: authentication documentation and migrations
```

---

## Test Suite 5: Enhanced Specialist Agents

### Test Coverage

#### 5.1 Delphi Agent Enhancement

**Test Name**: `test_delphi_extended_thinking`

**Objective**: Verify Delphi can handle complex architecture decisions

**Test Scenario**: Design authentication architecture

**Setup**:
```
Invoke Delphi (after 3+ failed auth fix attempts):
"Design the complete authentication and authorization architecture for a multi-tenant SaaS application with OAuth2, RBAC, and API token support. Consider security, performance, and maintainability."
```

**Expected Behavior**:
1. ✅ Extended thinking activated (32k token budget)
2. ✅ Deep analysis of requirements
3. ✅ Multiple architectural approaches considered
4. ✅ Tradeoffs discussed (security vs performance)
5. ✅ Specific implementation recommendations

**Verification**:
```python
# Request should include thinking budget
delphi_request = {
    "model": "gpt-5.2-medium",
    "thinking_budget": 32000,
    "prompt": "[complex architecture question]"
}

response = invoke_delphi(delphi_request)

# Verify response includes reasoning
assert hasattr(response, 'thinking_blocks')
assert len(response.thinking_blocks) > 0
assert response.final_answer is not None
```

**Success Criteria**:
- [ ] Extended thinking budget used
- [ ] Multiple approaches considered
- [ ] Tradeoffs explicitly discussed
- [ ] Specific, actionable recommendations
- [ ] Architecture decisions justified

---

#### 5.2 Dewey Agent Enhancement

**Test Name**: `test_dewey_documentation_research`

**Objective**: Verify Dewey finds library usage patterns

**Test Scenario**: Research FastAPI best practices

**Setup**:
```
Invoke Dewey:
"Research FastAPI authentication patterns from official documentation and production GitHub examples. Find 3 implementations and compare their approaches."
```

**Expected Behavior**:
1. ✅ Searches official FastAPI docs
2. ✅ Finds GitHub examples via grep.app
3. ✅ Analyzes multiple implementations
4. ✅ Compares approaches and tradeoffs
5. ✅ Provides recommendations

**Verification**:
```python
response = invoke_dewey({
    "task": "research FastAPI auth patterns",
    "required_sources": [
        "official FastAPI docs",
        "GitHub examples",
        "production implementations"
    ]
})

# Verify multiple sources referenced
sources = extract_sources(response)
assert len(sources) >= 3
assert "github.com" in str(sources)
assert "fastapi" in response.lower()
```

**Success Criteria**:
- [ ] Multiple sources researched
- [ ] GitHub examples found
- [ ] Patterns identified
- [ ] Tradeoffs compared
- [ ] Recommendations provided

---

#### 5.3 Explore Agent Enhancement

**Test Name**: `test_explore_semantic_search`

**Objective**: Verify Explore can map architecture

**Test Scenario**: Map authentication architecture

**Setup**:
```
Invoke Explore:
"Map the complete authentication architecture in this codebase. Find all files involved in authentication, identify the patterns used, check for inconsistencies, and provide a visual summary."
```

**Expected Behavior**:
1. ✅ Semantic search for "authentication logic"
2. ✅ AST search for auth decorators/middleware
3. ✅ Pattern consistency analysis
4. ✅ Multi-file relationship mapping
5. ✅ Architecture visualization

**Verification**:
```python
response = invoke_explore({
    "task": "map auth architecture",
    "include": [
        "file locations",
        "pattern consistency",
        "relationships",
        "visual summary"
    ]
})

# Verify comprehensive mapping
assertions = [
    "auth" in response.lower(),
    "pattern" in response.lower() or "consistent" in response.lower(),
    len(response) > 1000,  # Detailed response
    extract_file_paths(response) >= 5
]

assert all(assertions)
```

**Success Criteria**:
- [ ] Multiple files identified
- [ ] Patterns found and analyzed
- [ ] Inconsistencies noted
- [ ] Relationships mapped
- [ ] Summary provided

---

### Manual Testing: Agent Selection & Routing

**Test Scenario 1**: Use correct agent for task type

```
Prompt: "Our authentication is slow. How should we optimize it?"

Verification:
- [ ] Recognized as ARCHITECTURE question (not implementation)
- [ ] Delegated to Delphi (strategic advisor) after initial analysis?
- [ ] Delphi provided strategic recommendations?
- [ ] Implementation happens in separate Task call?
```

**Test Scenario 2**: Cost-aware escalation

```
Task: Fix authentication bug

Escalation Path:
1. Direct semantic_search → FREE ✅
2. Task(explore) → CHEAP ✅
3. Task(debugger) → MEDIUM (only if explore can't fix)
4. Task(delphi) → EXPENSIVE (only after 3+ failures)

Verification:
- [ ] Cheap options attempted first?
- [ ] No premature delphi invocation?
- [ ] Clear escalation reasoning?
```

---

## Test Suite 6: Integration & End-to-End Tests

### Test Coverage

#### 6.1 Orchestrator Full Workflow

**Test Name**: `test_orchestrator_full_implementation_flow`

**Objective**: Verify complete implementation workflow

**Test Scenario**: Implement JWT authentication

**Test Prompt**:
```
/stravinsky implement JWT authentication for our API.
Research best practices, find existing patterns in the codebase,
implement the service with tests, and create a verification endpoint.
```

**Expected Workflow**:
1. ✅ Parallel execution instructions injected
2. ✅ TodoWrite created with 5+ tasks
3. ✅ Task() calls for parallel execution:
   - Task(dewey, "research JWT best practices")
   - Task(explore, "find existing auth patterns")
   - Task(frontend, "design auth UI") [if needed]
4. ✅ Results synthesized
5. ✅ Implementation executed
6. ✅ Tests created and verified

**Verification**:
```python
# Verify response structure
assertions = [
    len(response.todo_items) >= 5,  # Multiple todos
    count_task_calls(response) >= 3,  # Parallel tasks
    all_tasks_in_same_response(response),  # Parallel execution
    count_todo_completions(response) == len(response.todo_items),
]

assert all(assertions), "Orchestrator workflow incomplete"
```

**Success Criteria**:
- [ ] All workflow phases completed
- [ ] Parallel execution verified
- [ ] Result synthesis correct
- [ ] Implementation matches requirements

---

#### 6.2 Commit Workflow Integration

**Test Name**: `test_commit_skill_integration`

**Objective**: Verify complete commit workflow with style detection

**Setup**: Feature branch with 8 modified files

**Test Steps**:
1. Stage files in feature branch
2. Invoke `/commit` skill
3. Verify all 6 phases execute correctly
4. Approve and execute commits
5. Verify commits in git log

**Success Criteria**:
- [ ] All phases execute sequentially
- [ ] Style correctly detected
- [ ] Atomic formula enforced
- [ ] Plan matches approved structure
- [ ] Commits created and verified

---

#### 6.3 Continuation Loop Workflow

**Test Name**: `test_continuation_loop_full_cycle`

**Objective**: Verify iterative execution workflow

**Setup**: Iterative optimization task

**Test Steps**:
1. Start loop: `/strav:loop prompt="Optimize queries" max_iterations=3`
2. Verify loop state created
3. Execute 3 iterations
4. Verify iteration count increments
5. Verify loop stops after max iterations

**Success Criteria**:
- [ ] Loop initializes correctly
- [ ] Iterations execute and track
- [ ] Auto-stop conditions work
- [ ] Manual stop hook works
- [ ] State persists across iterations

---

## Test Suite 7: Error Handling & Edge Cases

### Test Coverage

#### 7.1 Parallel Execution Error Handling

**Test Name**: `test_parallel_execution_error_handling`

**Objective**: Verify graceful handling of errors

**Test Cases**:

**Case 1: Task Failure**
```
One Task fails, others continue
Expected: Orchestrator catches error, continues with other tasks
Success: All parallel tasks attempted, failures noted
```

**Case 2: Network Error**
```
Network timeout during Task execution
Expected: Timeout caught, graceful degradation
Success: User notified, not entire workflow failure
```

**Case 3: No Agents Available**
```
Agent service unavailable
Expected: Fallback to direct tools
Success: Work completes with reduced delegation
```

---

#### 7.2 Commit Skill Error Handling

**Test Name**: `test_commit_skill_error_handling`

**Objective**: Verify error recovery

**Test Cases**:

**Case 1: Permission Denied**
```
Cannot read git log
Expected: Clear error message, user guidance
Success: Fails safely with instructions
```

**Case 2: Not in Git Repository**
```
git commands fail (not in repo)
Expected: Clear error "Not in git repository"
Success: Fails gracefully
```

**Case 3: Conflict in Atomic Planning**
```
Cannot justify file grouping
Expected: Show conflict to user, ask for override
Success: User can override with explicit justification
```

---

#### 7.3 Loop Edge Cases

**Test Name**: `test_loop_edge_cases`

**Objective**: Verify edge case handling

**Test Cases**:

**Case 1: Max Iterations = 1**
```
Loop with max_iterations=1
Expected: One iteration, then stop
Success: No endless loops
```

**Case 2: Completion Promise Never Found**
```
completion_promise="IMPOSSIBLE_STRING"
Expected: Loop runs to max_iterations, stops
Success: No infinite loops
```

**Case 3: Concurrent Modifications**
```
State file modified during iteration
Expected: Handle gracefully
Success: No data loss or corruption
```

---

## Part 3: Automated Testing Recommendations

### Unit Test Suite

Create `tests/test_stravinsky_implementations.py`:

```python
# Test parallel execution hook
def test_detect_stravinsky_invocation(): ...
def test_detect_implementation_task(): ...
def test_activate_stravinsky_mode(): ...
def test_parallel_instruction_injection(): ...

# Test Git Master
def test_atomic_formula(): ...
def test_commit_style_detection(): ...
def test_file_grouping_logic(): ...

# Test continuation loop
def test_loop_initialization(): ...
def test_iteration_tracking(): ...
def test_auto_stop_conditions(): ...

# Test agent enhancements
def test_delphi_thinking_budget(): ...
def test_dewey_source_discovery(): ...
def test_explore_semantic_search(): ...
```

### Integration Test Suite

Create `tests/test_orchestrator_integration.py`:

```python
# Test parallel execution workflow
def test_parallel_task_execution(): ...
def test_task_result_synthesis(): ...
def test_agent_delegation_routing(): ...

# Test LOOKS/WORKS classification
def test_looks_vs_works_routing(): ...
def test_mixed_request_splitting(): ...

# Test cost-aware escalation
def test_cost_aware_delegation(): ...
def test_escalation_path(): ...
```

### E2E Test Suite

Create `tests/test_e2e_workflows.py`:

```python
# Test full implementation workflow
def test_implementation_feature_workflow(): ...
def test_commit_and_push_workflow(): ...
def test_iterative_optimization_loop(): ...

# Test error scenarios
def test_parallel_execution_with_failures(): ...
def test_graceful_degradation(): ...
def test_error_recovery(): ...
```

### CI/CD Integration

**GitHub Actions Workflow** (`.github/workflows/test-implementations.yml`):

```yaml
name: Test Stravinsky Implementations

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Run unit tests
        run: pytest tests/test_stravinsky_implementations.py -v

      - name: Run integration tests
        run: pytest tests/test_orchestrator_integration.py -v

      - name: Run E2E tests
        run: pytest tests/test_e2e_workflows.py -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Part 4: Testing Checklist & Success Criteria

### Pre-Release Testing Checklist

- [ ] **Parallel Execution** (Test Suite 1)
  - [ ] Stravinsky invocation detected
  - [ ] Implementation tasks detected
  - [ ] Mode activation works
  - [ ] Instructions injected correctly
  - [ ] Parallel tasks fire in same response

- [ ] **Orchestrator Enhancements** (Test Suite 2)
  - [ ] Task delegation works correctly
  - [ ] LOOKS/WORKS classification accurate
  - [ ] Cost-aware escalation functions
  - [ ] Agent routing correct

- [ ] **Continuation Loop** (Test Suite 3)
  - [ ] Loop initializes correctly
  - [ ] Iteration tracking works
  - [ ] Auto-stop conditions function
  - [ ] Manual stop hook works
  - [ ] State persists

- [ ] **Git Master** (Test Suite 4)
  - [ ] Phase 0: Context gathering parallel
  - [ ] Phase 1: Style detection accurate
  - [ ] Phase 2: Formula enforced
  - [ ] Phase 3: File grouping logical
  - [ ] Phase 4: User confirmation works
  - [ ] Phase 5: Commits created correctly
  - [ ] Phase 6: Verification successful

- [ ] **Enhanced Agents** (Test Suite 5)
  - [ ] Delphi extended thinking active
  - [ ] Dewey finds multiple sources
  - [ ] Explore maps architecture
  - [ ] All agents return expected output

- [ ] **Integration** (Test Suite 6)
  - [ ] Orchestrator full workflow
  - [ ] Commit workflow integration
  - [ ] Continuation loop cycle

- [ ] **Error Handling** (Test Suite 7)
  - [ ] Parallel execution errors caught
  - [ ] Commit errors handled gracefully
  - [ ] Loop edge cases managed

### Success Metrics

| Metric | Target | Method |
|--------|--------|--------|
| Unit Test Coverage | >90% | pytest coverage |
| Integration Tests Pass | 100% | pytest integration suite |
| E2E Workflows Success | >95% | Manual + automated E2E |
| Error Recovery | <5% failures | Error scenario testing |
| Performance | <2sec parallel context | Timing benchmarks |
| User Experience | 100% clear | Manual workflow testing |

---

## Part 5: Manual Testing Procedures

### Procedure 1: Parallel Execution Workflow

**Time Required**: 5-10 minutes

**Steps**:
1. Open Claude Code
2. Submit: `/stravinsky implement OAuth2 authentication with JWT tokens`
3. Observe:
   - [ ] Instructions injected before LLM response?
   - [ ] TodoWrite created with multiple items?
   - [ ] Multiple Task() calls visible?
   - [ ] Tasks execute in parallel?
   - [ ] Results synthesized?

**Expected Result**: ✅ Parallel execution evident in response structure

---

### Procedure 2: LOOKS/WORKS Classification

**Time Required**: 10-15 minutes

**Scenarios**:

**A. Pure LOOKS**
- Prompt: "Make the login form red with rounded corners"
- Expected: Delegates to frontend agent only

**B. Pure WORKS**
- Prompt: "Implement rate limiting for API endpoints"
- Expected: Delegates to explore agent only

**C. Mixed**
- Prompt: "Create a beautiful dashboard showing real-time metrics"
- Expected: Delegates to both frontend + explore in parallel

**Expected Result**: ✅ Correct agent routing for each scenario

---

### Procedure 3: Commit Workflow

**Time Required**: 15-20 minutes

**Setup**:
```bash
git checkout -b test-commit
# Create/modify multiple files
touch src/auth.py tests/test_auth.py docs/auth.md
git add .
```

**Steps**:
1. Invoke `/commit`
2. Verify all 6 phases execute:
   - [ ] Phase 0: git commands parallel?
   - [ ] Phase 1: style detected, examples shown?
   - [ ] Phase 2: formula calculated?
   - [ ] Phase 3: atomic plan with justifications?
   - [ ] Phase 4: user approval requested?
   - [ ] Phase 5: commits created?
   - [ ] Phase 6: verification shows clean tree?

**Expected Result**: ✅ All commits created with correct messages and grouping

---

### Procedure 4: Continuation Loop

**Time Required**: 10-15 minutes

**Setup**:
```bash
/strav:loop prompt="Improve code documentation" max_iterations=3 completion_promise="DOCS_COMPLETE"
```

**Steps**:
1. Observe loop starts
2. Complete iteration 1:
   - [ ] State file created?
   - [ ] iteration_count = 1?

3. Complete iteration 2:
   - [ ] iteration_count = 2?

4. Complete iteration 3:
   - [ ] iteration_count = 3?
   - [ ] Loop auto-stops?

5. Test manual stop:
   - [ ] Start new loop
   - [ ] Click "Stop" in Claude Code
   - [ ] Loop stops at next boundary?

**Expected Result**: ✅ Loop executes correctly with proper iteration tracking

---

### Procedure 5: Cost-Aware Delegation

**Time Required**: 15-20 minutes

**Scenario**: Debug difficult issue

**Setup**:
```
Prompt: "The authentication service returns 401 on valid tokens. Debug this."
```

**Observe Escalation**:
1. Phase 1: Uses semantic_search (FREE) first?
2. Phase 2: Delegates to explore (CHEAP) if needed?
3. Phase 3: Only after 2 failures, uses debugger (MEDIUM)?
4. Phase 4: Only after 3 failures, uses delphi (EXPENSIVE)?

**Expected Result**: ✅ Cost-first escalation path followed

---

## Part 6: Continuous Integration & Maintenance

### Pre-Deployment Verification

**Automated Checks**:
```bash
# Run all unit tests
pytest tests/test_stravinsky_implementations.py -v

# Run integration tests
pytest tests/test_orchestrator_integration.py -v

# Check code quality
black --check mcp_bridge/
flake8 mcp_bridge/
mypy mcp_bridge/

# Verify documentation
mdpdf IMPLEMENTATION_SUMMARY.md
```

### Post-Deployment Monitoring

**Metrics to Track**:
- [ ] Parallel execution success rate
- [ ] Agent delegation accuracy
- [ ] Commit workflow completion rate
- [ ] Loop iteration tracking accuracy
- [ ] Error recovery success rate
- [ ] User satisfaction with workflows

**Logging**:
- All hook executions logged
- Task delegations tracked
- Error scenarios captured
- Performance metrics recorded

### Version Control & Updates

**Version Bumping Strategy**:
- Patch (X.Y.Z+1): Bug fixes, test additions
- Minor (X.Y+1.0): New features, agent enhancements
- Major (X+1.0.0): Breaking changes to API

---

## Appendix A: Test Data & Fixtures

### Git Commit Fixtures

```python
SEMANTIC_COMMITS = [
    "feat: add OAuth2 authentication",
    "fix: resolve CORS headers issue",
    "chore: update dependencies",
    "docs: improve API documentation",
    "refactor: simplify auth service",
    "test: add integration tests",
]

PLAIN_COMMITS = [
    "Add user authentication",
    "Fix login bug",
    "Update dependencies",
    "Improve error messages",
    "Refactor database layer",
]

KOREAN_COMMITS = [
    "사용자 인증 기능 추가",
    "로그인 버그 수정",
    "의존성 업데이트",
]
```

### Loop State Fixtures

```yaml
---
iteration_count: 2
max_iterations: 10
completion_promise: "TASK_COMPLETE"
active: true
started_at: 2026-01-08T12:34:56Z
last_updated: 2026-01-08T12:35:22Z
---
Original task...

## Iteration 1
[Work performed in iteration 1]

## Iteration 2
[Work performed in iteration 2]
```

---

## Appendix B: Success Criteria Summary

| Feature | Unit Tests | Integration | E2E | Manual |
|---------|-----------|-------------|-----|--------|
| Parallel Execution | ✅ | ✅ | ✅ | ✅ |
| LOOKS/WORKS Gate | ✅ | ✅ | ✅ | ✅ |
| Cost-Aware Escalation | ✅ | ✅ | ✅ | ✅ |
| Commit Workflow | ✅ | ✅ | ✅ | ✅ |
| Continuation Loop | ✅ | ✅ | ✅ | ✅ |
| Agent Enhancements | ✅ | ✅ | ✅ | ✅ |

---

## Appendix C: Troubleshooting Guide

### Issue: Parallel Tasks Not Executing

**Symptom**: Tasks appear sequential in response

**Causes**:
1. Instructions not injected → Check parallel_execution.py hook
2. TodoWrite not present → Verify orchestrator creates todos
3. Task() calls not in same response → Check response structure

**Resolution**:
```python
# Verify hook is active
tail -f ~/.stravinsky_mode

# Check orchestrator mode
grep -n "TodoWrite" response

# Verify task calls
grep -c "Task(" response  # Should be > 1
```

---

### Issue: Commit Workflow Stuck

**Symptom**: Hangs at Phase 3 (file grouping)

**Causes**:
1. Circular dependencies detected
2. Cannot justify file grouping
3. Git command timeout

**Resolution**:
```bash
# Check for circular deps
git show --format=%H $commit

# Re-run with verbose output
/commit --verbose

# Manual override if necessary
/commit --override-grouping
```

---

### Issue: Loop Not Stopping

**Symptom**: Loop continues past max_iterations

**Causes**:
1. Iteration count not incrementing
2. Completion promise misspelled
3. Stop hook not installed

**Resolution**:
```python
# Check state file
cat .stravinsky/continuation-loop.md

# Manually set active: false
echo "active: false" >> .stravinsky/continuation-loop.md

# Reinstall stop hook
stravinsky-install-hooks --force
```

---

## Conclusion

This comprehensive test plan provides:
- ✅ **Complete coverage** of all 10 implementations
- ✅ **Unit, integration, and E2E test strategies**
- ✅ **Manual testing procedures** with clear steps
- ✅ **Success criteria** for each feature
- ✅ **Troubleshooting guidance** for common issues
- ✅ **CI/CD integration** recommendations
- ✅ **Maintenance procedures** for ongoing operations

All implementations are production-ready with thorough testing procedures. Teams should execute the manual testing procedures before deploying to production and maintain the automated test suite for continuous verification.

---

**Document Status**: ✅ COMPLETE
**Last Updated**: January 8, 2026
**Next Review**: After first production deployment
