# 3-Way Merge Algorithm for Stravinsky

**Complete specification for automatic hook/skill updates with user customization preservation.**

---

## 📋 Documentation Index

### 1. **[MERGE_ALGORITHM_SUMMARY.md](./MERGE_ALGORITHM_SUMMARY.md)** ⭐ START HERE
**Executive summary and quick reference (5 min read)**

- Problem statement
- Algorithm overview (60 seconds)
- Key design principles
- File type handling summary
- Conflict detection overview
- Usage examples
- Glossary

**When to read**: First - get the big picture before diving into details.

---

### 2. **[3WAY_MERGE_ALGORITHM.md](./3WAY_MERGE_ALGORITHM.md)** 📊 DETAILED SPEC
**Complete algorithm specification with pseudocode (30 min read)**

**Contains**:
- Algorithm overview and architecture
- Conflict detection rules (detailed)
- File-type-specific merge rules:
  - Python hooks (AST-aware)
  - Markdown skills (section-based)
  - JSON configs (deep merge)
- Merge decision matrix (Python/Markdown/JSON)
- User customization preservation strategy
- Auto-mergeable vs manual review triggers
- Hook ordering and dependency handling
- Fallback behavior
- Full pseudocode for core algorithm
- Complete real-world scenario example (pre_tool_use.py)
- Edge cases and handling

**When to read**: After summary - implement according to this spec.

---

### 3. **[MERGE_IMPLEMENTATION_GUIDE.md](./MERGE_IMPLEMENTATION_GUIDE.md)** 💻 CODE PATTERNS
**Actual Python implementation code examples (45 min read)**

**Contains**:
- Module structure
- Type definitions (MergeResult, Conflict, etc.)
- Core merge function implementation
- Python handler with AST analysis
- Markdown handler with YAML parsing
- JSON handler with deep merge
- Integration with HookUpdateManager
- Testing patterns
- Deployment checklist
- Performance optimization strategies

**When to read**: Use as template while implementing in Python.

---

### 4. **[MERGE_TEST_CASES.md](./MERGE_TEST_CASES.md)** ✅ VALIDATION
**Comprehensive test cases and fixtures (40 min read)**

**Contains**:
- Test suite organization
- Python hook merge tests (5 scenarios)
- Markdown skill merge tests (4 scenarios)
- JSON config merge tests (4 scenarios)
- Integration tests (2 workflows)
- Edge case tests (4 scenarios)
- Regression tests
- Test fixtures and conftest
- Performance benchmarks
- Coverage goals
- CI/CD integration

**When to read**: After implementation - validate with these tests.

---

### 5. **[MERGE_DECISION_MATRIX.md](./MERGE_DECISION_MATRIX.md)** 🎯 QUICK REFERENCE
**Decision tables for every merge scenario (15 min read)**

**Contains**:
- Python imports resolution table
- Python function changes table
- Python flowchart
- Markdown metadata table
- Markdown sections table
- Markdown flowchart
- JSON simple keys table
- JSON nested objects table
- JSON arrays table
- JSON flowchart
- Universal decision flowchart
- Conflict marker examples (Python/Markdown/JSON)
- Severity reference table
- Resolution strategy by severity
- Quick decision guide
- Performance targets

**When to read**: During implementation and conflict resolution - check table for your scenario.

---

## 🚀 Quick Start

### For Architects/Decision Makers
1. Read: [MERGE_ALGORITHM_SUMMARY.md](./MERGE_ALGORITHM_SUMMARY.md) (5 min)
2. Review: Diagram sections in [3WAY_MERGE_ALGORITHM.md](./3WAY_MERGE_ALGORITHM.md) (10 min)
3. Decision: Approve 6-week implementation plan

### For Implementation Engineers
1. Read: [MERGE_ALGORITHM_SUMMARY.md](./MERGE_ALGORITHM_SUMMARY.md) (5 min)
2. Study: [3WAY_MERGE_ALGORITHM.md](./3WAY_MERGE_ALGORITHM.md) (30 min)
3. Implement: Follow [MERGE_IMPLEMENTATION_GUIDE.md](./MERGE_IMPLEMENTATION_GUIDE.md) (ongoing)
4. Check: Reference [MERGE_DECISION_MATRIX.md](./MERGE_DECISION_MATRIX.md) while coding
5. Test: Use [MERGE_TEST_CASES.md](./MERGE_TEST_CASES.md) (ongoing)

### For QA/Testing
1. Read: [MERGE_TEST_CASES.md](./MERGE_TEST_CASES.md) (40 min)
2. Setup: Configure test fixtures from `conftest.py`
3. Execute: Run tests from test suite
4. Validate: Check coverage goals (90%+)

### For Documentation/Support
1. Read: [MERGE_ALGORITHM_SUMMARY.md](./MERGE_ALGORITHM_SUMMARY.md) (5 min)
2. Reference: [MERGE_DECISION_MATRIX.md](./MERGE_DECISION_MATRIX.md) for user explanations
3. Bookmark: [Conflict Marker Examples](#conflict-markers) section

---

## 📊 Document Relationships

```
START
  ↓
MERGE_ALGORITHM_SUMMARY.md ⭐ (Overview)
  ├→ Executive understanding
  ├→ Problem/solution
  ├→ Key concepts
  └→ Next: Choose role
      ↓
      ┌─────────┬──────────┬─────────┐
      ↓         ↓          ↓         ↓
   ARCHITECT  ENGINEER   QA      SUPPORT
      ↓         ↓          ↓         ↓
    APPROVE  3WAY_MERGE  TEST_    DECISION_
    PLAN     ALGORITHM   CASES    MATRIX
      ↓         ↓          ↓         ↓
    ✅        IMPL.      ✅       ✅
    APPROVED  GUIDE      COVERAGE DOCS
              ↓
            CODE
              ↓
            ✅
            DEPLOYED
```

---

## 🎯 Key Concepts

### Three-Way Merge
Merges three versions: BASE (original), OURS (user modified), THEIRS (framework updated)
- Preserves both user customizations AND framework updates
- Auto-merges when safe, requires manual review when conflicted

### Conflict Severity
- **CRITICAL (0.0)**: Parse errors, missing data → Manual fix
- **HIGH (0.2)**: Function/value conflicts → Requires review
- **MEDIUM (0.6)**: Minor overlaps → Can auto-resolve
- **LOW (0.9)**: Non-overlapping → Auto-resolvable
- **NONE (1.0)**: No conflicts → Auto-merge

### Confidence Score
- Score: 0.0 to 1.0
- Threshold: >0.95 → Auto-merge ✅
- Below: >0.95 → Manual review ⚠️

### File Types Supported
1. **Python** (`.py`) - AST-aware merge for hooks
2. **Markdown** (`.md`) - Section-based merge for skills
3. **JSON** (`.json`) - Deep recursive merge for configs

---

## 📈 Implementation Phases

| Phase | Duration | Tasks | Status |
|-------|----------|-------|--------|
| 1: Foundation | Week 1 | Core algorithm, conflict detection | ✅ Spec |
| 2: Python Handler | Week 1-2 | AST merge, imports, functions | ⏳ Ready |
| 3: Markdown Handler | Week 2 | YAML merge, sections | ⏳ Ready |
| 4: JSON Handler | Week 2 | Deep merge, arrays | ⏳ Ready |
| 5: Integration | Week 3 | Update manager, notifications | ⏳ Ready |
| 6: Testing/Deploy | Week 3-4 | Tests, benchmarks, rollout | ⏳ Ready |

---

## 🔄 Merge Workflow

```
User Requests Hook Update
         ↓
Framework Provides New Version (v1.1)
         ↓
Stravinsky Detects Hook Change
         ↓
Load Three Versions:
  ├─ BASE (v1.0)
  ├─ OURS (current user)
  └─ THEIRS (v1.1)
         ↓
Perform Three-Way Merge
         ↓
┌────────┴────────┐
↓                 ↓
✅ SUCCESS       ⚠️ CONFLICT
  ↓               ↓
AUTO-MERGE     MANUAL REVIEW
  ↓               ↓
Write Result    Create .CONFLICT File
  ↓               ↓
Done ✅          User Resolves ✅
```

---

## 🛡️ Safety Guarantees

✅ **User customizations always preserved**
- If user added code → kept
- If user modified function → preserved
- If user added import → kept

✅ **Framework updates applied safely**
- New features → added when non-conflicting
- Bug fixes → applied when non-conflicting
- Improvements → accepted when non-conflicting

✅ **Never loses data**
- Always backup before changing
- Fall back to current version on error
- Conflict markers preserve all versions

✅ **Transparent conflicts**
- Clear conflict markers
- Show BASE, OURS, THEIRS
- Explain what changed and why

---

## 📚 Examples

### Example 1: Auto-Merge (User adds import, Framework improves function)

```
BASE:     import sys; def hook(): pass
OURS:     import logging, sys; def hook(): pass    (user added logging)
THEIRS:   import sys; def hook(name): pass         (framework improved)

RESULT:   import logging, sys; def hook(name): pass ✅
          (Both changes preserved)
```

### Example 2: Conflict (Both modify same function)

```
BASE:     def hook(): return allow()
OURS:     def hook():              (user added check)
            if user_check():
              return allow()
THEIRS:   def hook():              (framework added check)
            if admin_check():
              return allow()

RESULT:   ⚠️ CONFLICT
          (User needs to decide which check to use)
```

### Example 3: Skill Update (Framework updates doc, user adds example)

```
BASE:     ---
          description: Skill
          ---
          # Title
          Usage here

OURS:     ---
          description: Skill
          ---
          # Title
          Usage here
          ## Examples           (user added)
          - Example 1

THEIRS:   ---
          description: Updated Skill
          version: 1.1
          ---
          # Title
          Updated usage info

RESULT:   ---
          description: Updated Skill    (THEIRS)
          version: 1.1                  (THEIRS)
          ---
          # Title
          Updated usage info             (THEIRS)
          ## Examples                    (OURS - preserved)
          - Example 1
          ✅ (Both preserved)
```

---

## 🧪 Validation Checklist

Before deployment, verify:

- [ ] All 5 documents read and understood
- [ ] Python handler implemented and tested
- [ ] Markdown handler implemented and tested
- [ ] JSON handler implemented and tested
- [ ] Core algorithm implemented and tested
- [ ] All test cases passing (90%+ coverage)
- [ ] Performance benchmarks met (<1s for typical files)
- [ ] Integration with HookUpdateManager complete
- [ ] Conflict notification system working
- [ ] Backup mechanism in place
- [ ] User documentation prepared
- [ ] Beta testing completed
- [ ] Production rollout plan ready

---

## 🚨 Troubleshooting

### "Merge failed with parse error"
→ Check file encoding and syntax
→ See: Edge Cases section in 3WAY_MERGE_ALGORITHM.md

### "Confidence score too low"
→ Review conflicts in MERGE_DECISION_MATRIX.md
→ May require manual resolution

### "Import conflict detected"
→ User and framework both use same import differently
→ See: Python Imports Resolution table

### "Metadata type mismatch"
→ Framework changed value type (int→string)
→ See: Metadata Type Mismatch test case

---

## 📖 Related Documentation

- **Architecture**: See `.claude/agents/HOOKS.md` for hook system
- **Implementation**: See `mcp_bridge/hooks/` for existing hook code
- **Config**: See `.claude/settings.json` for hook configuration
- **Updates**: See hook update workflow documentation

---

## 🔗 File Locations in Codebase

```
stravinsky/
├── docs/                          # This documentation
│   ├── MERGE_README.md            # This file
│   ├── 3WAY_MERGE_ALGORITHM.md    # Algorithm spec
│   ├── MERGE_ALGORITHM_SUMMARY.md # Quick reference
│   ├── MERGE_IMPLEMENTATION_GUIDE.md # Code patterns
│   ├── MERGE_TEST_CASES.md        # Test scenarios
│   └── MERGE_DECISION_MATRIX.md   # Decision tables
├── mcp_bridge/
│   ├── merge/                     # Merge module (to create)
│   │   ├── __init__.py
│   │   ├── core.py
│   │   ├── conflict_detector.py
│   │   ├── conflict_resolver.py
│   │   └── handlers/
│   │       ├── python_handler.py
│   │       ├── markdown_handler.py
│   │       └── json_handler.py
│   └── hooks/
│       └── update_manager.py      # Integration point
└── tests/
    └── merge/                     # Test files (to create)
        ├── test_python_merge.py
        ├── test_markdown_merge.py
        ├── test_json_merge.py
        └── conftest.py
```

---

## 💾 File Sizes

| Document | Size | Read Time | Purpose |
|----------|------|-----------|---------|
| MERGE_README.md | 8KB | 5 min | You are here |
| MERGE_ALGORITHM_SUMMARY.md | 11KB | 10 min | Quick reference |
| 3WAY_MERGE_ALGORITHM.md | 28KB | 30 min | Complete spec |
| MERGE_IMPLEMENTATION_GUIDE.md | 35KB | 45 min | Code patterns |
| MERGE_TEST_CASES.md | 18KB | 40 min | Test validation |
| MERGE_DECISION_MATRIX.md | 16KB | 15 min | Decision tables |
| **TOTAL** | **116KB** | **2.5 hours** | Full knowledge |

---

## 🎓 Learning Path

### 30-Minute Overview (For Executives)
1. MERGE_ALGORITHM_SUMMARY.md (5 min)
2. Problem/Solution section (5 min)
3. Key principles (5 min)
4. Success criteria (5 min)
5. Implementation phases (5 min)

### 2-Hour Deep Dive (For Architects)
1. All of 30-min overview (30 min)
2. 3WAY_MERGE_ALGORITHM.md sections 1-7 (60 min)
3. MERGE_DECISION_MATRIX.md overview (30 min)

### 6-Hour Implementation (For Engineers)
1. All of 2-hour deep dive (2 hours)
2. MERGE_IMPLEMENTATION_GUIDE.md full read (3 hours)
3. Reference MERGE_DECISION_MATRIX.md (1 hour)

### 10-Hour Full Mastery (For Core Team)
1. All of 6-hour implementation (6 hours)
2. MERGE_TEST_CASES.md full read (2 hours)
3. Implement + validate (2 hours)

---

## ✅ Success Criteria

- [ ] All documents understood by relevant stakeholders
- [ ] Implementation follows algorithm spec exactly
- [ ] Test coverage >90%
- [ ] Performance <1s for typical files
- [ ] User customizations preserved in 100% of cases
- [ ] Framework updates applied when safe
- [ ] Conflict markers generation working
- [ ] Fallback behavior prevents data loss
- [ ] Integration with HookUpdateManager complete
- [ ] User documentation published
- [ ] Beta testing passed
- [ ] Production deployment successful

---

## 📞 Questions?

Refer to the appropriate document:

| Question | Document |
|----------|----------|
| "What's the big picture?" | MERGE_ALGORITHM_SUMMARY.md |
| "How does the algorithm work?" | 3WAY_MERGE_ALGORITHM.md |
| "How do I implement this?" | MERGE_IMPLEMENTATION_GUIDE.md |
| "How do I test this?" | MERGE_TEST_CASES.md |
| "What do I do in scenario X?" | MERGE_DECISION_MATRIX.md |

---

**Status**: ✅ Complete Specification
**Created**: 2024-01-15
**Last Updated**: 2024-01-15
**Version**: 1.0
