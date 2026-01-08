# Hook & Skill System - Quick Reference Card

## HOOK INVENTORY (13 Total)

### ✅ TIER 1: System-Core (Auto-Merge Safe)
```
stravinsky_mode.py       PreToolUse   → Blocks Read/Grep/Bash during orchestrator mode
parallel_execution.py    UserPrompt   → Injects parallel execution, creates marker
todo_continuation.py     UserPrompt   → Reminds about incomplete TODOs
stop_hook.py            Stop         → Manages continuation loop (Ralph Wiggum)
context.py              UserPrompt   → Prepends local context (CLAUDE.md/README.md)
notification_hook.py    Notification → Formats agent spawn messages with emoji
tool_messaging.py       PostToolUse  → Formats MCP tool output
truncator.py            PostToolUse  → Truncates long output
pre_compact.py          PreCompact   → Pre-compaction prep
subagent_stop.py        SubagentStop → Subagent cleanup
```

### ⚠️ TIER 2: User-Facing (Manual Merge)
```
context_monitor.py      UserPrompt   → Tracks context usage (⚙️ customizable thresholds)
  Custom fields: MAX_CONTEXT_TOKENS, PREEMPTIVE_THRESHOLD, CRITICAL_THRESHOLD

edit_recovery.py        PostToolUse  → Edit tool error recovery (⚙️ customizable patterns)
  Custom fields: error_patterns list
```

### 📖 Documentation
```
CONTINUATION_LOOP_README.md (339 lines) → Ralph Wiggum loop implementation guide
```

---

## SKILL INVENTORY (16 Total)

### Root Skills
```
/strav              Stravinsky Orchestrator - parallel execution
/delphi             Strategic advisor (GPT-5.2-based)
/dewey              Documentation & research (Gemini + web search)
/commit             Git Master - atomic commits
/publish            Bump version, publish to PyPI
/verify             Post-implementation verification
/version            Show version info
/review             Code review with Gemini
/index              Index project for semantic search
```

### /str Namespace (Semantic Search)
```
/str:index          Semantic index builder
/str:search         Natural language code search
/str:start_filewatch Auto-reindexing file watcher
/str:stop_filewatch Stop file watcher
/str:stats          Index statistics viewer
```

### /strav Namespace (Orchestrator)
```
/strav:loop         Start continuation loop
/strav:cancel-loop  Cancel continuation loop
```

---

## HOOK DEPENDENCIES

```
🎯 Orchestrator Mode Flow
├── parallel_execution.py         (detects /stravinsky)
│   └── creates ~/.stravinsky_mode marker file
│       └── stravinsky_mode.py     (reads marker on PreToolUse)
│           └── blocks Read/Grep/Bash/Edit
│               └── todo_delegation.py (checks marker on TodoWrite)

🔄 Continuation Loop Flow
├── stop_hook.py                  (reads .stravinsky/continuation-loop.md)
│   ├── increments iteration_count
│   └── checks completion_promise
│       └── injects continuation prompt (exit code 2)

⚠️ Context Monitoring Flow
├── context_monitor.py            (on UserPromptSubmit)
│   ├── estimates token usage
│   └── at 70%: pre-emptive warning
│   └── at 85%: critical warning
│       └── writes ~/.claude/state/context_monitor.json

📝 TODO Tracking Flow
├── todo_continuation.py          (on UserPromptSubmit)
│   ├── reads .claude/todo_state.json
│   └── injects TODO reminders
├── todo_delegation.py            (on TodoWrite)
│   └── checks stravinsky_mode status
```

---

## STATE FILES & MARKERS

| Location | Purpose | Format | Lifecycle |
|----------|---------|--------|-----------|
| `~/.stravinsky_mode` | Orchestrator marker | JSON | Created by parallel_execution.py, read by stravinsky_mode.py |
| `~/.claude/state/context_monitor.json` | Context tracking | JSON | Updated by context_monitor.py |
| `.claude/todo_state.json` | TODO tracking | JSON | Updated by TodoWrite tool |
| `.stravinsky/continuation-loop.md` | Loop state | YAML frontmatter | Created by user/skill, managed by stop_hook.py |

---

## MERGE STRATEGY MATRIX

| Scenario | Type | Action | Effort |
|----------|------|--------|--------|
| TIER 1 file changed, no other changes | SYSTEM_ONLY | ✅ Auto-merge | Low |
| TIER 2 file changed, no customizations | AUTO_MERGE | ✅ Auto-merge | Low |
| TIER 2 file changed, user customized | MANUAL_MERGE | ⚠️ Manual review | Medium |
| Both TIER 1 & TIER 2 changed | FULL_MERGE | ⚠️ Manual review | High |
| No files changed | NO_CHANGE | ⏭️ Skip | None |

---

## VERSION TRACKING (Recommended)

### Current State (v0.3.9)
- ❌ No explicit hook versioning
- ❌ No skill versioning metadata
- ❌ No merge validation automation

### Target State (v0.4.0+)

**Add to each hook**:
```python
HOOK_VERSION = "1.0.0"
MIN_PACKAGE_VERSION = "0.3.9"
TIER = "system-core"  # or "user-facing"
```

**Create .claude/hooks/VERSIONS.md**:
- Metadata table for all hooks
- Changelog entries
- Dependency information

**Implement merge_strategy.py**:
```bash
python merge_strategy.py --analyze              # Detect customizations
python merge_strategy.py --validate             # Check settings
python merge_strategy.py --merge <new_hooks>    # Generate merge report
```

---

## CUSTOMIZATION GUIDE

### context_monitor.py - Safe Ranges

```python
MAX_CONTEXT_TOKENS = 200000      # Range: 100000-500000
PREEMPTIVE_THRESHOLD = 0.70      # Range: 0.50-0.80 (when to warn)
CRITICAL_THRESHOLD = 0.85        # Range: 0.75-0.95 (when to panic)
CHARS_PER_TOKEN = 4              # Range: 3-5 (token estimation)
```

**How to customize**:
```bash
# Edit .claude/hooks/context_monitor.py and change values
# Example: More aggressive warnings (warn at 60% instead of 70%)
PREEMPTIVE_THRESHOLD = 0.60
```

### edit_recovery.py - Add Error Patterns

```python
error_patterns = [
    r"oldString not found",
    r"oldString matched multiple times",
    r"line numbers out of range",
    r"Your Custom Pattern Here",  # Add your patterns
]
```

---

## LIFECYCLE HOOKS REFERENCE

| Lifecycle | When Fired | Purpose | Max Handlers |
|-----------|-----------|---------|-------------|
| **Notification** | Any event | User messaging | ∞ |
| **SubagentStop** | Subagent stops | Cleanup | ∞ |
| **PreCompact** | Before compact | State prep | ∞ |
| **PreToolUse** | Before tool runs | Allow/block decisions | ∞ |
| **UserPromptSubmit** | User input | Inject instructions | ∞ |
| **PostToolUse** | After tool runs | Format output | ∞ |
| **Stop** | Response ends | Continue decision | ∞ |

---

## COMMON TASKS

### Check Customizations
```bash
python .stravinsky/merge_strategy.py --analyze
```

### Validate Before Merge
```bash
python .stravinsky/merge_strategy.py --validate
```

### Generate Merge Report
```bash
python .stravinsky/merge_strategy.py --merge /path/to/new/hooks
```

### Emergency Rollback
```bash
# Restore previous hooks
git checkout v0.3.9 -- .claude/hooks/

# Clean state files
rm -f ~/.stravinsky_mode
rm -rf ~/.claude/state/
rm -f .stravinsky/continuation-loop.md
```

### Verify Hook Syntax
```bash
for hook in .claude/hooks/*.py; do
    python3 -m py_compile "$hook" || echo "ERROR: $hook"
done
```

### Test Hook Execution
```bash
echo '{"prompt": "test"}' | \
    python3 .claude/hooks/parallel_execution.py
```

---

## TROUBLESHOOTING

| Problem | Cause | Solution |
|---------|-------|----------|
| "STRAVINSKY MODE ACTIVE" message | /stravinsky invoked | Normal - use Task() instead of Read/Grep/Bash |
| Context warnings at 70% | Monitor triggered | Normal - generate summary to compact context |
| Edit tool failure | oldString mismatch | Re-read file, ensure exact whitespace match |
| Continuation loop won't stop | completion_promise not found | Check if promise text appears exactly in response |
| "MANUAL MERGE REQUIRED" | User customizations | Run merge_strategy.py, preserve custom values |

---

## DOCUMENTATION STRUCTURE

```
.stravinsky/
├── HOOK_SKILL_ANALYSIS.md         ← Start here (comprehensive)
├── VERSION_TRACKING_SPEC.md       ← Version strategy (detailed)
├── ANALYSIS_SUMMARY.md            ← Executive summary (overview)
├── QUICK_REFERENCE.md             ← This file (cheat sheet)
└── merge_strategy.py              ← Tool (CLI validation)

Key Sections:
- HOOK_SKILL_ANALYSIS: Sections 1-4 (structure & strategy)
- VERSION_TRACKING_SPEC: Parts 1-3 (versioning approach)
- merge_strategy.py: Main class + CLI (implementation)
```

---

## KEY NUMBERS

```
Total Hooks:                 13
├── System-core (TIER 1):   10
├── User-facing (TIER 2):    2
└── Documentation:           1

Total Skills:               16
├── Root:                    9
├── /str namespace:          5
└── /strav namespace:        2

Hooks with External State:  3
├── stravinsky_mode.py      (uses ~/.stravinsky_mode)
├── context_monitor.py      (uses ~/.claude/state/context_monitor.json)
└── stop_hook.py           (uses .stravinsky/continuation-loop.md)

Average Hook Size:          ~150 lines
Largest Hook:               tool_messaging.py (264 lines)
Documentation Volume:       CONTINUATION_LOOP_README.md (339 lines)

Test Coverage:
├── stop_hook.py:           6 test cases (all passing)
├── Other hooks:            Basic tests (✅ assumed passing)
└── Skills:                 Functional tests (✅ assumed passing)
```

---

## RECOMMENDED READING ORDER

**For Understanding**:
1. This file (QUICK_REFERENCE.md) - Get overview
2. HOOK_SKILL_ANALYSIS.md Section 1-2 - Hook categorization
3. ANALYSIS_SUMMARY.md - Key findings

**For Implementation**:
1. VERSION_TRACKING_SPEC.md Part 1-2 - Versioning approach
2. merge_strategy.py docstring - Implementation details
3. VERSION_TRACKING_SPEC.md Part 5 - Timeline & phases

**For Troubleshooting**:
1. This file - Troubleshooting section
2. HOOK_SKILL_ANALYSIS.md Section 8 - Testing
3. VERSION_TRACKING_SPEC.md Part 6 - Rollback

---

## NEXT STEPS

### Immediate (This Week)
- [ ] Review ANALYSIS_SUMMARY.md
- [ ] Run `python merge_strategy.py --analyze`
- [ ] Verify no customizations detected

### Short-term (v0.3.10 Planning)
- [ ] Add HOOK_VERSION to each hook
- [ ] Create .claude/hooks/VERSIONS.md
- [ ] Test merge_strategy.py validation

### Medium-term (v0.4.0 Release)
- [ ] Implement .versions.yml metadata
- [ ] Add pre-merge validation to CI/CD
- [ ] Document merge procedures

---

## Document Metadata

- **File**: QUICK_REFERENCE.md
- **Version**: 1.0
- **Size**: ~400 lines
- **Updated**: 2025-01-08
- **Package**: Stravinsky v0.3.9
- **Status**: ACTIVE (reference guide)

---

**For detailed information, see the full analysis documents in .stravinsky/**
