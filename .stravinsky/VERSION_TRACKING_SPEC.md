# Version Tracking Specification
## Hook & Skill Versioning for Stravinsky v0.3.9+

---

## OVERVIEW

This specification defines how hook and skill versions should be tracked, validated, and migrated across Stravinsky package releases.

**Current State**: v0.3.9
- Hooks: No explicit version tracking (implicit = package version)
- Skills: No explicit version tracking (implicit = package version)

**Target State**: v0.3.10+
- Hooks: Embedded semantic versioning + metadata file
- Skills: Frontmatter metadata with version constraints
- Infrastructure: Pre-merge validation and migration support

---

## PART 1: HOOK VERSIONING

### 1.1 Embedded Hook Versioning

Each hook file should include version metadata in docstring:

```python
#!/usr/bin/env python3
"""
Hook Name: Stravinsky Mode Enforcer
Version: 1.0.0
Package Version: 0.3.9
Last Updated: 2025-01-08

Description:
    PreToolUse hook that blocks native file tools (Read, Grep, Bash)
    when orchestrator mode is active, enforcing Task() delegation.

Exit Codes:
    0 = Allow the tool to execute
    2 = Block the tool (reason sent via stderr)

Changelog:
    1.0.0 (2025-01-08, v0.3.9): Initial implementation
        - PreToolUse enforcement for Read/Grep/Bash/Edit/MultiEdit
        - Marker file at ~/.stravinsky_mode
        - Hard blocking with exit code 2

Dependencies:
    - parallel_execution.py (creates marker file)
    - settings.json (defines hook entry point)

Lifecycle Point: PreToolUse
Matcher: Read,Search,Grep,Bash,Edit,MultiEdit
"""

# Constants (for validation)
HOOK_VERSION = "1.0.0"
MIN_PACKAGE_VERSION = "0.3.9"
```

### 1.2 Hook Versioning Constants

Add these constants to each hook:

```python
# Versioning metadata (DO NOT CHANGE MANUALLY)
HOOK_VERSION = "1.0.0"          # Semantic version of hook
MIN_PACKAGE_VERSION = "0.3.9"   # Minimum package version
MAX_PACKAGE_VERSION = None      # Max package (None = no limit)
TIER = "system-core"            # system-core or user-facing
```

### 1.3 Version Validation at Runtime

Optional: Add validation function to hook:

```python
def validate_version():
    """Validate hook version is compatible with package."""
    import importlib.metadata

    try:
        package_version = importlib.metadata.version("stravinsky")
        if package_version < MIN_PACKAGE_VERSION:
            print(
                f"⚠️  Hook v{HOOK_VERSION} requires stravinsky >= {MIN_PACKAGE_VERSION}, "
                f"but installed version is {package_version}",
                file=sys.stderr
            )
            # Don't exit - allow graceful degradation
    except Exception:
        pass  # Package not installed or version check failed
```

---

## PART 2: HOOK METADATA FILE

Create `.claude/hooks/VERSIONS.md` to centralize version information:

```markdown
# Hook Versions
## Stravinsky v0.3.9

**Generated**: 2025-01-08
**Package Version**: 0.3.9
**Total Hooks**: 13

---

## System-Core Hooks (Auto-Merge Safe)

These hooks implement infrastructure and should be updated automatically.

### stravinsky_mode.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: PreToolUse
- **Tier**: system-core
- **Dependencies**: parallel_execution.py (uses ~/.stravinsky_mode marker)
- **Last Updated**: 2025-01-08
- **Changes**: Initial implementation
- **Testing**: ✅ Full test coverage

### parallel_execution.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: UserPromptSubmit
- **Tier**: system-core
- **Dependencies**: stravinsky_mode.py (creates marker), todo_delegation.py
- **Last Updated**: 2025-01-08
- **Changes**: Initial implementation with /stravinsky detection
- **Testing**: ✅ Full test coverage

### todo_continuation.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: UserPromptSubmit
- **Tier**: system-core
- **Dependencies**: None
- **Last Updated**: 2025-01-08
- **Changes**: Initial implementation with TODO reminders
- **Testing**: ✅ Full test coverage

### stop_hook.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: Stop
- **Tier**: system-core
- **Dependencies**: None
- **Last Updated**: 2025-01-08
- **Changes**: Ralph Wiggum continuation loop implementation
- **Testing**: ✅ 6 test cases passing

### context.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: UserPromptSubmit
- **Tier**: system-core
- **Dependencies**: None
- **Last Updated**: 2025-01-08
- **Changes**: Initial implementation with local context loading
- **Testing**: ✅ Basic tests

### notification_hook.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: Notification
- **Tier**: system-core
- **Dependencies**: None
- **Last Updated**: 2025-01-08
- **Changes**: Agent spawn notification formatting
- **Testing**: ✅ Basic tests

### tool_messaging.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: PostToolUse
- **Tier**: system-core
- **Dependencies**: None
- **Last Updated**: 2025-01-08
- **Changes**: MCP tool message formatting with emoji
- **Testing**: ✅ Comprehensive emoji mapping tests

### truncator.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: PostToolUse
- **Tier**: system-core
- **Dependencies**: None
- **Last Updated**: 2025-01-08
- **Changes**: Output truncation utility
- **Testing**: ✅ Basic tests

### pre_compact.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: PreCompact
- **Tier**: system-core
- **Dependencies**: None
- **Last Updated**: 2025-01-08
- **Changes**: Initial implementation
- **Testing**: ⚠️ Basic tests

### subagent_stop.py
- **Version**: 1.0.0
- **Package**: v0.3.9 (added in 0.3.9)
- **Lifecycle**: SubagentStop
- **Tier**: system-core
- **Dependencies**: None
- **Last Updated**: 2025-01-08
- **Changes**: Initial implementation
- **Testing**: ⚠️ Basic tests

---

## User-Facing Hooks (Manual Merge Required)

These hooks have user-customizable parameters. Manual review required on updates.

### context_monitor.py
- **Version**: 1.0.2
- **Package**: v0.3.9 (added in 0.3.7, updated in 0.3.8)
- **Lifecycle**: UserPromptSubmit
- **Tier**: user-facing
- **Dependencies**: None
- **Last Updated**: 2024-12-15 (minor threshold adjustments)
- **Customizable Fields**:
  - `MAX_CONTEXT_TOKENS`: 100000-500000 (default: 200000)
  - `PREEMPTIVE_THRESHOLD`: 0.50-0.80 (default: 0.70)
  - `CRITICAL_THRESHOLD`: 0.75-0.95 (default: 0.85)
  - `CHARS_PER_TOKEN`: 3-5 (default: 4)
- **Migration Strategy**: Preserve user customizations, update logic only
- **Testing**: ✅ Full test coverage

### edit_recovery.py
- **Version**: 1.0.1
- **Package**: v0.3.9 (added in 0.3.8)
- **Lifecycle**: PostToolUse (Edit, MultiEdit)
- **Tier**: user-facing
- **Dependencies**: None
- **Last Updated**: 2024-12-01 (added new error pattern)
- **Customizable Fields**:
  - `error_patterns`: User can add custom patterns for their use cases
- **Migration Strategy**: Preserve user-added patterns, update built-in patterns
- **Testing**: ✅ Pattern matching tests

---

## Documentation

### CONTINUATION_LOOP_README.md
- **Type**: Documentation (not executable)
- **Version**: 1.0.0
- **Package**: v0.3.9
- **Last Updated**: 2025-01-08
- **Content**: 339 lines covering Ralph Wiggum loop implementation
- **Sections**:
  - Overview and implementation status
  - Key features with code examples
  - Quick start guide
  - Hook flow diagram
  - Test results (6 tests, all passing)
  - Troubleshooting and manual control
  - Architecture details and constants
  - Future enhancements

---

## Version History

### v0.3.9 (2025-01-08)
- Initial hook and skill system
- 10 system-core hooks
- 2 user-facing hooks
- 16 skills across 3 namespaces
- Ralph Wiggum continuation loop (stop_hook.py)

### v0.3.8 (2024-12-15)
- Added context_monitor.py (user-facing)
- Added edit_recovery.py (user-facing)
- Improved error handling in hooks

### v0.3.7 (2024-12-01)
- Initial hook infrastructure

---
```

---

## PART 3: SKILL VERSIONING

### 3.1 Enhanced Skill Frontmatter

Update skill frontmatter to include version metadata:

```yaml
---
description: Stravinsky Orchestrator - parallel agent execution for complex workflows
version: 1.0.0
package_version: ">=0.3.9,<1.0.0"
depends_hooks:
  - stravinsky_mode.py: ">=1.0.0"
  - parallel_execution.py: ">=1.0.0"
  - todo_delegation.py: ">=1.0.0"
depends_skills:
  - /version: ">=1.0.0"
requires_tools:
  - agent_spawn
  - task_delegation
  - invoke_gemini
  - invoke_openai
allowed-tools: Agent, Skill, TodoWrite, Read, Grep, Glob
---
```

### 3.2 Skill Metadata Requirements

| Field | Type | Required | Example |
|-------|------|----------|---------|
| `description` | string | ✅ YES | "Stravinsky Orchestrator - ..." |
| `version` | semver | ✅ YES | "1.0.0" |
| `package_version` | semver constraint | ✅ YES | ">=0.3.9,<1.0.0" |
| `depends_hooks` | dict | ❌ NO | `stravinsky_mode.py: ">=1.0.0"` |
| `depends_skills` | dict | ❌ NO | `/version: ">=1.0.0"` |
| `requires_tools` | list | ❌ NO | `[agent_spawn, task_delegation]` |
| `allowed-tools` | list | ✅ YES | `[Agent, Skill, TodoWrite]` |

### 3.3 Skill Version Bumping Rules

**Patch Bump** (1.0.0 → 1.0.1):
- Bug fixes in skill logic
- Updated documentation
- No changes to interface or dependencies

**Minor Bump** (1.0.0 → 1.1.0):
- New features added
- Enhanced functionality
- Backward compatible
- May add new `depends_hooks` or `depends_skills`

**Major Bump** (1.0.0 → 2.0.0):
- Breaking changes to interface
- Removed features
- Changed `requires_tools`
- Incompatible hook dependency changes

---

## PART 4: VALIDATION & MIGRATION

### 4.1 Pre-Merge Validation

Run before applying hook/skill updates:

```bash
#!/bin/bash
set -e

echo "=== PRE-MERGE VALIDATION ==="

# 1. Syntax check all Python hooks
echo "Checking Python syntax..."
for hook in .claude/hooks/*.py; do
    python3 -m py_compile "$hook" || {
        echo "❌ Syntax error: $hook"
        exit 1
    }
done

# 2. Validate JSON settings
echo "Validating settings.json..."
python3 -c "import json; json.load(open('.claude/settings.json'))" || {
    echo "❌ Invalid JSON: .claude/settings.json"
    exit 1
}

# 3. Check version metadata
echo "Checking version metadata..."
for hook in .claude/hooks/*.py; do
    if ! grep -q "HOOK_VERSION = " "$hook"; then
        echo "⚠️  Missing HOOK_VERSION in $hook"
    fi
done

# 4. Validate skill frontmatter
echo "Checking skill metadata..."
for skill in .claude/commands/**/*.md; do
    if ! grep -q "^description:" "$skill"; then
        echo "❌ Missing description in $skill"
        exit 1
    fi
done

echo "✅ All pre-merge checks passed"
```

### 4.2 Post-Merge Validation

Run after applying updates:

```bash
#!/bin/bash
set -e

echo "=== POST-MERGE VALIDATION ==="

# 1. Test hook execution with sample input
echo "Testing hook execution..."
echo '{"prompt": "test prompt"}' | \
    python3 .claude/hooks/parallel_execution.py > /dev/null || {
    echo "❌ Hook execution failed"
    exit 1
}

# 2. Verify state files exist
echo "Checking state file directories..."
mkdir -p ~/.claude/state 2>/dev/null || true
mkdir -p .stravinsky 2>/dev/null || true

# 3. Check hook interdependencies
echo "Validating hook dependencies..."
if grep -q "\.stravinsky_mode" .claude/hooks/*.py 2>/dev/null; then
    echo "  ✅ stravinsky_mode marker references found"
fi

echo "✅ All post-merge checks passed"
```

### 4.3 Format Migration

When hook file format changes between versions, migrate automatically:

```python
def migrate_hook_format(old_version: str, new_version: str, hook_content: str) -> str:
    """Migrate hook content to new format."""

    if old_version == "0.3.9" and new_version == "0.4.0":
        # Example: Add new constant HOOK_VERSION if missing
        if "HOOK_VERSION = " not in hook_content:
            hook_content = hook_content.replace(
                'HOOK_VERSION = "1.0.0"',
                'HOOK_VERSION = "1.0.0"  # Added in 0.4.0',
                1
            )

    return hook_content
```

---

## PART 5: IMPLEMENTATION TIMELINE

### Phase 1: v0.3.10 (1-2 weeks)

**Minimal Version Tracking**:
- [ ] Add `HOOK_VERSION` constant to each hook docstring
- [ ] Create `.claude/hooks/VERSIONS.md` documentation
- [ ] Add minimal version validation to hooks
- [ ] Update test suite for version constants

**Example commit**:
```
feat: add embedded hook versioning for v0.3.10

- Add HOOK_VERSION constant to each hook (1.0.0)
- Create .claude/hooks/VERSIONS.md with metadata
- Add version validation to hook entry points
- All hooks track: version, package_version, tier, dependencies
```

### Phase 2: v0.4.0 (3-4 weeks)

**Structured Metadata & Validation**:
- [ ] Create `.claude/hooks/.versions.yml` (YAML metadata)
- [ ] Implement pre-merge validation script
- [ ] Add customization detection for TIER 2 hooks
- [ ] Generate automated merge conflict reports

**Example commit**:
```
feat: implement structured hook versioning and merge validation

- Add .claude/hooks/.versions.yml with complete metadata
- Implement merge_strategy.py for pre-merge analysis
- Auto-detect customizations in context_monitor.py and edit_recovery.py
- Generate merge conflict resolution reports
- Tests: 15 new test cases for merge detection
```

### Phase 3: v0.5.0 (6-8 weeks)

**Enhanced Skills Versioning & Independent Hook Updates**:
- [ ] Add version metadata to skill frontmatter
- [ ] Implement semantic version constraint checking
- [ ] Enable independent hook updates via new `/update-hook` skill
- [ ] Create hook marketplace framework

**Example commit**:
```
feat: implement skill versioning and independent hook updates

- Add version constraints to all skill frontmatter (18 skills)
- Implement semver constraint validation
- Add /update-hook skill for selective hook updates
- Enable hook versioning independent of package version
- Tests: 20 new test cases for version constraints
```

---

## PART 6: ROLLBACK & DISASTER RECOVERY

### 6.1 Version Rollback Procedure

If a hook update introduces regressions:

```bash
#!/bin/bash
# Rollback to previous version

VERSION_OLD="0.3.9"
VERSION_NEW="0.3.10"

echo "Rolling back from v${VERSION_NEW} to v${VERSION_OLD}..."

# 1. Restore hook files from git
git checkout v${VERSION_OLD} -- .claude/hooks/

# 2. Verify restoration
echo "Verifying restoration..."
for hook in .claude/hooks/*.py; do
    python3 -m py_compile "$hook" || {
        echo "❌ Restored hook has syntax errors: $hook"
        exit 1
    }
done

# 3. Clean marker files
rm -f ~/.stravinsky_mode
rm -rf ~/.claude/state/

# 4. Restart Claude Code
echo "✅ Rollback complete. Restart Claude Code to apply changes."
```

### 6.2 State File Recovery

If state files become corrupted:

```bash
#!/bin/bash
# Clean up state files to restore normal operation

echo "Cleaning up state files..."

# 1. Remove orchestrator mode marker
rm -f ~/.stravinsky_mode

# 2. Clear context monitor state
rm -f ~/.claude/state/context_monitor.json

# 3. Stop continuation loop
rm -f .stravinsky/continuation-loop.md

# 4. Clear todo state
rm -f .claude/todo_state.json

echo "✅ State files cleaned. Normal operation resumed."
```

---

## PART 7: REFERENCE & CONSTANTS

### Hook Version Schema

```
HOOK_VERSION = "{major}.{minor}.{patch}"

Where:
  major: Breaking API changes (0 = can change without warning)
  minor: New features, backward compatible
  patch: Bug fixes, documentation

Examples:
  1.0.0 = First stable release of hook
  1.0.1 = Bug fix in 1.0.0
  1.1.0 = New feature added
  2.0.0 = Breaking API change
```

### Lifecycle Points

```
Notification    → Fires on any notification event
SubagentStop    → Fires when subagent stops
PreCompact      → Fires before context compaction
PreToolUse      → Fires before tool execution (can block with exit 2)
UserPromptSubmit → Fires when user submits prompt
PostToolUse     → Fires after tool execution
Stop            → Fires when assistant stops generating
```

### Exit Codes

```
0 = Success (allow tool execution)
1 = Warning (tool executes, warning displayed)
2 = Hard Block (tool blocked, execution stops)
```

---

## Document Metadata

- **Version**: 1.0.0
- **Last Updated**: 2025-01-08
- **Package Version**: 0.3.9
- **Status**: ACTIVE
- **Next Review**: v0.3.10 release

---

## Appendix: Quick Reference

### Add Version Tracking to New Hook

```python
#!/usr/bin/env python3
"""
Hook Name: My New Hook
Version: 1.0.0
Package Version: 0.3.10
Last Updated: 2025-01-15

Description:
    What does this hook do?

Exit Codes:
    0 = Success
    2 = Block
"""

import json
import sys

# Versioning metadata
HOOK_VERSION = "1.0.0"
MIN_PACKAGE_VERSION = "0.3.10"
TIER = "system-core"  # or "user-facing"

def main():
    try:
        data = json.load(sys.stdin)
    except:
        return 0

    # Your hook logic here

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Add Version to Skill Frontmatter

```yaml
---
description: My Skill - Short description
version: 1.0.0
package_version: ">=0.3.10,<1.0.0"
depends_hooks:
  - my_hook.py: ">=1.0.0"
allowed-tools: Bash, Read, Edit
---

# Skill Implementation

Your skill content here...
```

---

END OF SPECIFICATION
