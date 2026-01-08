# Hook & Skill Structure Analysis
## Stravinsky v0.3.9 - Version Tracking & Merge Strategy

**Document Version**: 1.0
**Analysis Date**: 2025-01-08
**Current Package Version**: 0.3.9

---

## EXECUTIVE SUMMARY

The Stravinsky hook and skill system comprises:
- **13 hooks** across 5 lifecycle points (Notification, SubagentStop, PreCompact, PreToolUse, UserPromptSubmit, PostToolUse, Stop)
- **16 skills** organized in 3 namespaces (root, /str, /strav)
- **Complex interdependencies** requiring careful version tracking and merge strategy

**Key Finding**: Hooks have **embedded versioning logic** (no explicit version tags), while skills operate on **convention-based versioning** tied to package version.

---

## SECTION 1: HOOK CATEGORIZATION

### 1.1 SYSTEM-CORE HOOKS (Infrastructure - Auto-Merge Safe)

These hooks implement core Stravinsky behavior and should auto-merge during updates:

| Hook | Lifecycle | Purpose | Auto-Merge? | Conflict Risk |
|------|-----------|---------|------------|---------------|
| **stravinsky_mode.py** | PreToolUse | Enforces task delegation during /stravinsky | ✅ YES | Low - logic is stable |
| **parallel_execution.py** | UserPromptSubmit | Injects parallel execution instructions | ✅ YES | Low - pattern injection |
| **todo_continuation.py** | UserPromptSubmit | Reminds about incomplete TODOs | ✅ YES | Low - state file based |
| **stop_hook.py** | Stop | Continuation loop handler (Ralph Wiggum) | ✅ YES | Medium - YAML parsing |
| **context.py** | UserPromptSubmit | Prepends local context files | ✅ YES | Low - file discovery |
| **notification_hook.py** | Notification | User-friendly agent spawn messages | ✅ YES | Low - display only |
| **tool_messaging.py** | PostToolUse | Formats MCP tool messages with emoji | ✅ YES | Low - formatting logic |
| **truncator.py** | PostToolUse | Truncates PostToolUse output | ✅ YES | Low - utility function |
| **pre_compact.py** | PreCompact | Pre-compaction hook | ✅ YES | Low - infrastructure |
| **subagent_stop.py** | SubagentStop | Stops running subagents | ✅ YES | Low - lifecycle mgmt |

**Merge Strategy for System-Core**:
- ✅ Always auto-merge version bumps
- ⚠️ Test for conflicts in entry point paths
- 🔄 Update if: dependencies change, lifecycle hooks modified, new features added
- 📋 Require: full test suite pass before merge

---

### 1.2 USER-FACING / CUSTOMIZABLE HOOKS (User-Specific - Manual Merge)

These hooks affect user behavior and may be customized per project:

| Hook | Lifecycle | Purpose | Auto-Merge? | Customization Level |
|------|-----------|---------|------------|-------------------|
| **context_monitor.py** | UserPromptSubmit | Context usage warnings at 70%/85% | ⚠️ MANUAL | **HIGH** - thresholds adjustable |
| **edit_recovery.py** | PostToolUse | Edit tool error recovery | ⚠️ MANUAL | **MEDIUM** - error patterns |

**Merge Strategy for User-Facing**:
- ❌ Do NOT auto-merge - preserve user customizations
- 🔍 Check for conflicts in: thresholds (context_monitor) and error patterns (edit_recovery)
- 📝 Provide migration guide if hook logic changes
- 🧪 Allow side-by-side testing before overwriting

**Context Monitor Customizable Fields** (lines 18-22):
```python
MAX_CONTEXT_TOKENS = 200000      # User-adjustable
CHARS_PER_TOKEN = 4              # Tuning parameter
PREEMPTIVE_THRESHOLD = 0.70      # User threshold (70%)
CRITICAL_THRESHOLD = 0.85        # User threshold (85%)
```

**Edit Recovery Customizable Fields** (lines 25-28):
```python
error_patterns = [               # User can add custom patterns
    r"oldString not found",
    r"oldString matched multiple times",
    r"line numbers out of range"
]
```

---

### 1.3 DOCUMENTATION HOOKS (Reference Materials)

| Hook | Type | Purpose | Versioned? |
|------|------|---------|-----------|
| **CONTINUATION_LOOP_README.md** | Documentation | Ralph Wiggum loop implementation guide | ✅ YES (embedded in README) |

**Content**: 339 lines of comprehensive documentation, test results, troubleshooting.
**Version Tracking**: Uses markdown headers for sections; no explicit version tag needed.

---

## SECTION 2: HOOK LIFECYCLE & DEPENDENCY MAP

### 2.1 HOOK CREATION WORKFLOW

```
User runs /stravinsky skill
    ↓
parallel_execution.py detects /stravinsky invocation (line 22-30)
    ↓
Activates stravinsky_mode: creates ~/.stravinsky_mode marker file (line 65-67)
    ↓
On next PreToolUse event:
stravinsky_mode.py reads marker file (line 59-61)
    ↓
If file exists AND tool in BLOCKED_TOOLS (Read/Grep/Bash/Edit):
    → Blocks tool, suggests Task() delegation (line 96-139)
    → Exits with code 2 (hard block)
```

### 2.2 HOOK INTERDEPENDENCIES

**Direct Dependencies**:

```
stravinsky_mode.py (PreToolUse)
    ↓ reads marker
parallel_execution.py (UserPromptSubmit)
    ↓ creates marker at ~/.stravinsky_mode

todo_delegation.py (PostToolUse:TodoWrite)
    ↓ checks if stravinsky_mode active (line 51)
    → if YES: exit code 2 (hard block)
    → if NO: exit code 1 (warning)

todo_continuation.py (UserPromptSubmit)
    ↓ checks state file (.claude/todo_state.json)
    ↓ coexists with stop_hook.py (different message format, no conflicts)

stop_hook.py (Stop)
    ↓ checks state file (.stravinsky/continuation-loop.md)
    ↓ reads YAML frontmatter (iteration_count, max_iterations, completion_promise, active)
    ↓ injects continuation prompt on exit code 2

context_monitor.py (UserPromptSubmit)
    ↓ estimates token usage from conversation length
    ↓ triggers pre-emptive compact at 70%, critical at 85%
    ↓ writes state file (~/.claude/state/context_monitor.json)

edit_recovery.py (PostToolUse:Edit/MultiEdit)
    ↓ checks tool_response for error patterns
    ↓ injects recovery instruction if error detected
```

### 2.3 HOOK STATE FILES

| State File | Purpose | Format | Lifecycle |
|-----------|---------|--------|-----------|
| `~/.stravinsky_mode` | Marks orchestrator mode active | JSON | Created by parallel_execution.py, read by stravinsky_mode.py, deleted when exiting mode |
| `~/.claude/state/context_monitor.json` | Tracks last compact recommendation | JSON | Updated by context_monitor.py on 70%/85% thresholds |
| `.claude/todo_state.json` | Tracks incomplete todos | JSON | Updated by TodoWrite tool, read by todo_continuation.py |
| `.stravinsky/continuation-loop.md` | Ralph Wiggum loop state | YAML frontmatter | Created by user/skill, read/updated by stop_hook.py |

### 2.4 HOOK-TO-SETTINGS MAPPING

From `.claude/settings.json` (lines 2-108):

```json
"Notification": notification_hook.py
"SubagentStop": subagent_stop.py
"PreCompact": pre_compact.py
"PreToolUse": stravinsky_mode.py (matcher: Read,Search,Grep,Bash,Edit,MultiEdit)
"UserPromptSubmit": [
    context_monitor.py,
    parallel_execution.py,
    context.py,
    todo_continuation.py
]
"PostToolUse": [
    truncator.py (all events),
    tool_messaging.py (mcp__stravinsky__*, mcp__grep-app__*, Task),
    edit_recovery.py (Edit, MultiEdit),
    todo_delegation.py (TodoWrite)
]
```

**Execution Order** (same lifecycle point = sequential):
1. UserPromptSubmit: context_monitor → parallel_execution → context → todo_continuation
2. PostToolUse: truncator → tool_messaging → edit_recovery → todo_delegation

---

## SECTION 3: SKILL METADATA EXTRACTION

### 3.1 SKILL INVENTORY

| Skill Path | Description | Dependencies | Versioning |
|-----------|-------------|--------------|-----------|
| `/strav` | Stravinsky Orchestrator - parallel agent execution | agent_spawn, task delegation | Package v0.3.9 |
| `/strav:loop` | Continuation loop handler | stop_hook.py | Package v0.3.9 |
| `/strav:cancel-loop` | Cancel continuation loop | stop_hook.py | Package v0.3.9 |
| `/delphi` | Strategic advisor (GPT-5.2-based) | invoke_openai | Package v0.3.9 |
| `/dewey` | Documentation & research specialist | invoke_gemini, web_search | Package v0.3.9 |
| `/review` | Code review agent | invoke_gemini | Package v0.3.9 |
| `/commit` | Git Master - atomic commits | bash, git tools | Package v0.3.9 |
| `/publish` | Bump version, publish to PyPI | bash, pyproject.toml | Package v0.3.9 |
| `/verify` | Post-implementation verification | lsp_diagnostics, pytest | Package v0.3.9 |
| `/version` | Show version info | current_version | Package v0.3.9 |
| `/index` | Index project for semantic search | semantic_index | Package v0.3.9 |
| `/str:index` | Stravinsky semantic index | semantic_index | Package v0.3.9 |
| `/str:search` | Semantic code search | semantic_search | Package v0.3.9 |
| `/str:start_filewatch` | Start file watcher for reindexing | start_file_watcher | Package v0.3.9 |
| `/str:stop_filewatch` | Stop file watcher | stop_file_watcher | Package v0.3.9 |
| `/str:stats` | Semantic search index stats | semantic_stats | Package v0.3.9 |

### 3.2 SKILL FRONTMATTER STRUCTURE

Example from `publish.md` (lines 1-4):
```yaml
---
description: Bump version, publish to PyPI, and upgrade local installation
allowed-tools: Bash, Read, Edit
---
```

**Metadata Fields**:
- `description`: Human-readable purpose
- `allowed-tools`: Tools available to skill (optional)

**Current Limitation**: No explicit `version`, `dependencies`, or `requires_hooks` fields.

### 3.3 HOOK-SKILL DEPENDENCIES

```
SKILLS THAT REQUIRE HOOKS:

/strav (Orchestrator)
    → requires: stravinsky_mode.py (PreToolUse enforcement)
    → requires: parallel_execution.py (activation logic)
    → requires: todo_delegation.py (TodoWrite handling)

/strav:loop, /strav:cancel-loop (Continuation)
    → requires: stop_hook.py (state file management)

/commit (Git Master)
    → requires: all hooks (normal operation)
    → uses: tool_messaging.py (status output)

/publish (PyPI Release)
    → requires: all hooks (normal operation)
    → uses: context.py (reading CLAUDE.md)

/verify (Post-Implementation)
    → requires: all hooks (normal operation)
    → uses: tool_messaging.py, edit_recovery.py (diagnostics)
```

---

## SECTION 4: MERGE STRATEGY RECOMMENDATIONS

### 4.1 FILE CATEGORIZATION FOR MERGING

**TIER 1: Auto-Merge Safe** (never need manual review)
```
.claude/hooks/stravinsky_mode.py
.claude/hooks/parallel_execution.py
.claude/hooks/stop_hook.py
.claude/hooks/todo_continuation.py
.claude/hooks/notification_hook.py
.claude/hooks/tool_messaging.py
.claude/hooks/context.py
.claude/hooks/truncator.py
.claude/hooks/pre_compact.py
.claude/hooks/subagent_stop.py
.claude/hooks/CONTINUATION_LOOP_README.md
```

**TIER 2: Manual Review Required** (check for user customizations)
```
.claude/hooks/context_monitor.py    # Check thresholds (70%, 85%, MAX_CONTEXT_TOKENS)
.claude/hooks/edit_recovery.py       # Check error patterns
```

**TIER 3: Configuration** (merge into settings with conflict detection)
```
.claude/settings.json
```

**TIER 4: Skills** (follow package version, no independent versioning)
```
.claude/commands/**/*.md
```

### 4.2 MERGE CONFLICT DETECTION RULES

**Pre-Merge Checks**:

1. **Hook File Hash Comparison**:
   ```bash
   # For TIER 1 files: simple hash comparison
   md5 .claude/hooks/stravinsky_mode.py
   ```

2. **Customization Detection** (TIER 2):
   ```python
   # For context_monitor.py, check if these values differ from defaults:
   MAX_CONTEXT_TOKENS != 200000
   PREEMPTIVE_THRESHOLD != 0.70
   CRITICAL_THRESHOLD != 0.85

   # For edit_recovery.py, check if error_patterns list was modified
   ```

3. **Settings.json Validation**:
   ```bash
   # Ensure all hook entry points are present
   grep -c "notification_hook.py" .claude/settings.json   # should be 1
   grep -c "stravinsky_mode.py" .claude/settings.json     # should be 1
   ```

4. **Hook Dependency Validation**:
   ```bash
   # Verify marker files still exist in expected locations
   # ~/.stravinsky_mode
   # ~/.claude/state/context_monitor.json
   # .claude/todo_state.json
   # .stravinsky/continuation-loop.md
   ```

### 4.3 MERGE STRATEGY WORKFLOW

```
NEW VERSION RELEASED (e.g., 0.3.10)
    ↓
STEP 1: Pre-Merge Analysis
    - Hash check all TIER 1 files against current version
    - Scan TIER 2 files for customizations:
        context_monitor.py: extract current thresholds
        edit_recovery.py: extract current error patterns
    - Validate settings.json structure

    ↓
STEP 2: Determine Merge Type

    IF all TIER 1 files unchanged:
        → AUTO-MERGE (safe)

    IF any TIER 1 file changed:
        → FULL MERGE (new features/fixes)
        → Requires: full test suite pass
        → Requires: validation of hook interactions

    IF any TIER 2 file changed AND user customizations detected:
        → MANUAL MERGE REQUIRED
        → Provide: side-by-side comparison
        → Provide: migration guide (preserve customizations)

    IF settings.json changed:
        → MERGE WITH VALIDATION
        → Ensure: all hook entry points valid
        → Ensure: matcher patterns match actual hook capabilities

    ↓
STEP 3: Apply Merge

    FOR TIER 1 files: Direct overwrite

    FOR TIER 2 files:
        IF no customizations: Direct overwrite
        IF customizations: Preserve user values, update logic

    FOR settings.json: Merge JSON, preserve user hook additions

    FOR skills (.claude/commands/): Direct overwrite

    ↓
STEP 4: Post-Merge Validation
    - Verify hook syntax: python3 -m py_compile .claude/hooks/*.py
    - Validate settings.json: jsonschema validation
    - Test hook execution with sample inputs
    - Run full integration test suite
```

---

## SECTION 5: VERSION TRACKING IMPLEMENTATION

### 5.1 CURRENT STATE

**Package Version Sources**:
- `pyproject.toml` (line ~5): `version = "0.3.9"`
- `mcp_bridge/__init__.py`: `__version__ = "0.3.9"`

**Hook Versioning**: **EMBEDDED IN DOCSTRINGS**
```python
# Example from stravinsky_mode.py (lines 1-18)
"""
Stravinsky Mode Enforcer Hook

This PreToolUse hook blocks native file reading tools...
Exit codes:
  0 = Allow the tool to execute
  2 = Block the tool (reason sent via stderr)
"""
# NO EXPLICIT VERSION TAG - version is implicit (same as package)
```

**Skill Versioning**: **FOLLOWS PACKAGE VERSION**
```yaml
# Example from strav.md (lines 1-4)
---
description: /strav - Stravinsky Orchestrator - Relentless parallel agent execution for complex workflows.
---
# NO VERSION FIELD - implicitly v0.3.9 (package version)
```

### 5.2 RECOMMENDED VERSION TRACKING APPROACH

**Option A: Embedded Semantic Versioning** (Recommended)

Add version metadata to each hook:

```python
# .claude/hooks/stravinsky_mode.py
"""
Stravinsky Mode Enforcer Hook
Version: 1.0.0 (package v0.3.9)

This PreToolUse hook blocks native file reading tools...
Changelog:
  1.0.0 (v0.3.9): Initial implementation, PreToolUse enforcement
"""

# Constants
HOOK_VERSION = "1.0.0"
MIN_PACKAGE_VERSION = "0.3.9"
```

**Benefits**:
- ✅ Explicit version per hook
- ✅ Track when hook was last updated relative to package
- ✅ Support independent hook updates without package bumps
- ✅ Enable hook-specific deprecation warnings

**Implementation**:
```python
# Add validation at hook start
if HOOK_VERSION < expected_version:
    print(f"⚠️ Hook version mismatch: expected {expected_version}, got {HOOK_VERSION}")
```

---

**Option B: Metadata File** (Alternative)

Create `.claude/hooks/VERSIONS.md`:

```markdown
# Hook Versions (Stravinsky v0.3.9)

## System-Core Hooks
- stravinsky_mode.py: v1.0.0 (added in 0.3.9)
- parallel_execution.py: v1.0.0 (added in 0.3.9)
- stop_hook.py: v1.0.0 (added in 0.3.9)
- todo_continuation.py: v1.0.0 (added in 0.3.9)
...

## User-Facing Hooks
- context_monitor.py: v1.0.2 (last updated in 0.3.8, customizable in 0.3.9)
- edit_recovery.py: v1.0.1 (updated in 0.3.8)

## Changelog
### 0.3.9
- stravinsky_mode.py: Initial release
- parallel_execution.py: Initial release
- Added YAML frontmatter parsing to stop_hook.py
```

**Benefits**:
- ✅ Centralized version tracking
- ✅ Human-readable changelog
- ✅ Version history across package releases
- ✅ Easier to scan for compatibility issues

**Drawback**: Requires manual synchronization during updates

---

**Option C: Hybrid** (Recommended for Production)

Combine both approaches:
1. Add `HOOK_VERSION = "1.0.0"` to each hook
2. Maintain `.claude/hooks/VERSIONS.md` as source of truth
3. CI/CD validates consistency before release

```yaml
# .claude/hooks/.versions.yml
schema_version: "1"
package_version: "0.3.9"
hooks:
  stravinsky_mode.py:
    version: "1.0.0"
    added_in_package: "0.3.9"
    last_updated: "2025-01-08"
    tier: "system-core"
  context_monitor.py:
    version: "1.0.2"
    added_in_package: "0.3.7"
    last_updated: "2024-12-15"
    tier: "user-facing"
    customizable_fields:
      - "MAX_CONTEXT_TOKENS"
      - "PREEMPTIVE_THRESHOLD"
      - "CRITICAL_THRESHOLD"
```

### 5.3 VERSION BUMP TRIGGERS

**Patch Bump** (X.Y.Z → X.Y.Z+1):
- Bug fixes in hooks (not affecting behavior)
- Documentation updates (CONTINUATION_LOOP_README.md)
- Error message improvements

**Minor Bump** (X.Y.Z → X.Y+1.0):
- New hooks added
- New skills added
- Hook logic improvements (non-breaking)
- New customizable parameters

**Major Bump** (X.Y.Z → X+1.0.0):
- Breaking changes to hook interface
- Changes to state file format (.stravinsky/continuation-loop.md)
- Changes to marker file locations (~/.stravinsky_mode)
- Skills removed or significantly refactored

---

## SECTION 6: IMPLEMENTATION ROADMAP

### Phase 1: Immediate (v0.3.10)
- [ ] Add `HOOK_VERSION` constant to each hook
- [ ] Create `.claude/hooks/VERSIONS.md` documentation
- [ ] Add version check function to hook entry points:
  ```python
  def validate_hook_version(min_version="1.0.0"):
      if HOOK_VERSION < min_version:
          raise RuntimeError(f"Hook version {HOOK_VERSION} < {min_version}")
  ```

### Phase 2: Short-term (v0.4.0)
- [ ] Create `.claude/hooks/.versions.yml` metadata file
- [ ] Implement pre-merge validation script:
  ```bash
  ./.claude/hooks/validate_versions.py --mode pre-merge
  ```
- [ ] Add customization detection for TIER 2 hooks
- [ ] Generate merge conflict report automatically

### Phase 3: Long-term (v0.5.0+)
- [ ] Support independent hook versioning (v1.0.0 of hook in v0.3.9 of package)
- [ ] Enable selective hook updates without full package update
- [ ] Implement hook deprecation warnings
- [ ] Create skill-specific version constraints (e.g., `/publish` requires `/version` v1.0+)

---

## SECTION 7: MERGE CONFLICT EXAMPLES

### Example 1: Safe Auto-Merge (stravinsky_mode.py)

**Current Version (v0.3.9)**:
```python
BLOCKED_TOOLS = {
    "Read", "Search", "Grep", "Bash", "MultiEdit", "Edit",
}
```

**New Version (v0.3.10)**:
```python
BLOCKED_TOOLS = {
    "Read", "Search", "Grep", "Bash", "MultiEdit", "Edit", "Glob",  # Added "Glob"
}
```

**Action**: ✅ AUTO-MERGE (no user customization possible)

---

### Example 2: Manual Merge Required (context_monitor.py)

**Current Version (v0.3.9)** - User customized:
```python
MAX_CONTEXT_TOKENS = 150000      # User set to 150k (not 200k)
PREEMPTIVE_THRESHOLD = 0.60      # User set to 60% (not 70%)
```

**New Version (v0.3.10)**:
```python
MAX_CONTEXT_TOKENS = 200000      # Default increased
PREEMPTIVE_THRESHOLD = 0.70      # Default unchanged
```

**Merge Conflict**:
- Detect: `MAX_CONTEXT_TOKENS` differs from package default
- Action: ❌ DO NOT OVERWRITE
- Resolution: Present user with choice:
  - Keep custom (150000)
  - Update to new default (200000)
  - Override with another value

---

### Example 3: State File Migration (continuation-loop.md)

**Current Format (v0.3.9)**:
```yaml
---
iteration_count: 5
max_iterations: 10
completion_promise: "Tests passing"
active: true
---
```

**New Format (v0.4.0)**:
```yaml
---
iteration_count: 5
max_iterations: 10
completion_promise: "Tests passing"
active: true
timeout_seconds: 3600          # New field added
retry_on_failure: false         # New field added
---
```

**Migration Strategy**:
1. Check if `.stravinsky/continuation-loop.md` exists
2. If v0.3.9 format detected:
   - Add default values for new fields
   - Preserve existing values
   - Log migration event

```python
def migrate_continuation_loop_format():
    """Migrate from v0.3.9 to v0.4.0 format"""
    if not CONTINUATION_LOOP_FILE.exists():
        return True

    state, remaining = parse_yaml_frontmatter(CONTINUATION_LOOP_FILE.read_text())

    # Add new fields with defaults if missing
    state.setdefault('timeout_seconds', 3600)
    state.setdefault('retry_on_failure', False)

    # Write back updated format
    new_frontmatter = dict_to_yaml(state)
    CONTINUATION_LOOP_FILE.write_text(new_frontmatter + remaining)
```

---

## SECTION 8: TESTING MERGE CHANGES

### Pre-Release Validation Checklist

```bash
#!/bin/bash
# Pre-release hook validation

echo "=== PHASE 1: SYNTAX VALIDATION ==="
for hook in .claude/hooks/*.py; do
    python3 -m py_compile "$hook" || echo "FAIL: $hook"
done

echo "=== PHASE 2: SETTINGS VALIDATION ==="
python3 -c "import json; json.load(open('.claude/settings.json'))" || echo "FAIL: settings.json"

echo "=== PHASE 3: HOOK EXECUTION TEST ==="
echo '{"prompt": "test prompt"}' | python3 .claude/hooks/parallel_execution.py > /dev/null
echo '{"toolName": "Read", "params": {"file_path": "test.py"}}' | python3 .claude/hooks/stravinsky_mode.py > /dev/null

echo "=== PHASE 4: DEPENDENCY CHECK ==="
# Verify marker file paths exist in expected locations
grep -r "\.stravinsky_mode" .claude/hooks/ > /dev/null || echo "WARN: No references to .stravinsky_mode"
grep -r "continuation-loop" .claude/hooks/ > /dev/null || echo "WARN: No continuation-loop references"

echo "=== PHASE 5: SKILL METADATA ==="
for skill in .claude/commands/**/*.md; do
    if ! grep -q "^description:" "$skill"; then
        echo "WARN: Missing description in $skill"
    fi
done

echo "✅ Pre-release validation complete"
```

---

## SECTION 9: RECOMMENDATIONS

### Short-term (Next 2-3 releases)

1. **Implement Option C (Hybrid Versioning)**
   - Add `HOOK_VERSION` to each hook
   - Create `.claude/hooks/VERSIONS.md`
   - Estimated effort: 2-3 hours

2. **Create Merge Validation Script**
   - Detect customizations in TIER 2 hooks
   - Validate settings.json entry points
   - Estimated effort: 1-2 hours

3. **Document Customization Points**
   - For each TIER 2 hook, document user-customizable fields
   - Provide per-field documentation and safe ranges
   - Estimated effort: 1 hour

### Medium-term (v0.4.0)

1. **Implement Structured Metadata**
   - Use `.claude/hooks/.versions.yml` (YAML)
   - Add `depends_on_hooks`, `depends_on_skills` fields
   - Add `customizable_fields` with safe value ranges

2. **Create Pre-Merge Validation CLI**
   - Automatic customization detection
   - Generate merge conflict report
   - Suggest conflict resolutions

3. **Update Skills Metadata**
   - Add `skill_version` to frontmatter
   - Add `requires_hooks` and `requires_skills` dependencies
   - Add `requires_package_version` constraint

### Long-term (v0.5.0+)

1. **Independent Hook Versioning**
   - Allow v1.5.0 of hook in v0.3.9 of package
   - Enable selective hook updates via skill `/update-hook`
   - Track hook version history separately

2. **Semantic Versioning for Skills**
   - Each skill gets independent version tracking
   - Skills can specify `requires_skill_version` dependencies
   - Enable selective skill updates

3. **Hook Marketplace**
   - Users can contribute custom hooks
   - Community hooks can be version-tracked separately
   - Official hooks marked as system-core vs community

---

## APPENDIX A: Hook Reference

### Hook Matchers (settings.json)

| Matcher | Meaning | Examples |
|---------|---------|----------|
| `*` | All events | Matches everything |
| `Read,Search,Grep,Bash,Edit,MultiEdit` | Specific tools | Matches only these tool names |
| `mcp__stravinsky__*` | Namespace wildcard | mcp__stravinsky__invoke_gemini, mcp__stravinsky__grep_search |
| `mcp__grep-app__*` | MCP server wildcard | mcp__grep-app__searchCode, mcp__grep-app__github_file |
| `Task` | Task tool only | Matches Task tool use |
| `TodoWrite` | TodoWrite only | Matches TodoWrite tool use |

### Hook Exit Codes

| Exit Code | Meaning | Behavior |
|-----------|---------|----------|
| 0 | Success (allow tool) | Tool executes normally |
| 1 | Warning | Tool executes, warning message sent |
| 2 | Hard block | Tool is blocked, error message sent, execution stops |

### Lifecycle Points

| Lifecycle | Fired | Purpose | Example Hooks |
|-----------|-------|---------|---------------|
| Notification | Any notification event | User-friendly messaging | notification_hook.py |
| SubagentStop | When subagent stops | Cleanup, state management | subagent_stop.py |
| PreCompact | Before context compaction | Pre-compaction state prep | pre_compact.py |
| PreToolUse | Before tool execution | Block/allow decisions | stravinsky_mode.py |
| UserPromptSubmit | When user submits prompt | State injection, reminders | parallel_execution.py, context.py, etc. |
| PostToolUse | After tool execution | Output formatting, recovery | tool_messaging.py, edit_recovery.py |
| Stop | When assistant stops | Continuation decisions | stop_hook.py |

---

## APPENDIX B: Customization Guide for Users

### Customizing context_monitor.py

Edit these lines to adjust context thresholds:

```python
# Line 18: Maximum context tokens (increase if you have more budget)
MAX_CONTEXT_TOKENS = 200000

# Line 20: Preemptive warning threshold (lower = more aggressive warnings)
PREEMPTIVE_THRESHOLD = 0.70  # 70%

# Line 21: Critical warning threshold (lower = more critical warnings)
CRITICAL_THRESHOLD = 0.85    # 85%

# Line 19: Token estimation (adjust if token counting seems off)
CHARS_PER_TOKEN = 4
```

**Safe Values**:
- `MAX_CONTEXT_TOKENS`: 100000 - 500000
- `PREEMPTIVE_THRESHOLD`: 0.50 - 0.80
- `CRITICAL_THRESHOLD`: 0.75 - 0.95
- `CHARS_PER_TOKEN`: 3 - 5

### Customizing edit_recovery.py

Add custom error patterns for your workflows:

```python
# Line 25-29: Add patterns for errors you commonly encounter
error_patterns = [
    r"oldString not found",
    r"oldString matched multiple times",
    r"line numbers out of range",
    r"Your Custom Error Pattern",  # Add here
]
```

---

## Document Metadata

- **Version**: 1.0
- **Last Updated**: 2025-01-08
- **Package Version**: 0.3.9
- **Total Hooks Analyzed**: 13
- **Total Skills Analyzed**: 16
- **Merge Strategy**: Tier-based (4 tiers)
- **Next Review**: v0.3.10 release
