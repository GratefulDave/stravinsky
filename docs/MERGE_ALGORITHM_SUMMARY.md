# 3-Way Merge Algorithm - Executive Summary

**Status**: Complete Specification ✅

**Deliverables**:
1. ✅ Algorithm specification with pseudocode
2. ✅ Implementation guide with code examples
3. ✅ Test cases and validation strategy
4. ✅ File type-specific merge rules
5. ✅ Conflict detection and resolution
6. ✅ User customization preservation strategy

---

## Quick Reference

### What Problem Does This Solve?

When Stravinsky updates hooks or skills, user customizations are preserved automatically using a 3-way merge algorithm inspired by Git. This prevents data loss while keeping framework updates.

**Before**: User updates → Framework update → Data loss (user changes overwritten)

**After**: User updates + Framework update → Smart merge (both preserved) ✅

---

## Algorithm in 60 Seconds

```
BASE (v1.0)          OURS (User)         THEIRS (v1.1)
     |                    |                   |
     └────────────────────┼───────────────────┘
                          |
                    ANALYZE CHANGES
                          |
            ┌─────────────┼─────────────┐
            |             |             |
        NO CONFLICT   CONFLICT      ERROR
            |             |             |
        AUTO-MERGE   MANUAL REVIEW  FALLBACK
            |             |             |
           ✅             ⚠️             ❌
```

---

## Key Design Principles

### 1. Preserve User Customizations
- If user added code → Keep it
- If user modified function → Preserve modifications
- If user added import → Keep the import

### 2. Accept Framework Updates
- New framework features → Accept when no conflict
- Framework improvements (type hints, docs) → Accept
- Framework fixes → Accept when no conflict

### 3. Fail Safely
- When unsure → Ask user (conflict marker)
- When error → Keep current version
- Always backup before changing

### 4. Be Transparent
- Show all conflicts in human-readable format
- Explain what changed and why
- Provide clear resolution instructions

---

## File Type Handling

### Python Hooks

| Component | Strategy | Auto-Merge? |
|-----------|----------|------------|
| Imports | Union (combine all) | ✅ Always |
| Functions | AST-aware 3-way diff | ⚠️ Depends on changes |
| Comments | Keep THEIRS (newer) | ✅ Always |
| Structure | Preserve order | ✅ Always |

**Example**:
```python
# BASE: import logging + def hook()
# OURS: import logging + custom_func() + def hook()
# THEIRS: from typing import Dict + def hook() (improved)
# RESULT: All imports + custom_func + improved hook ✅
```

### Markdown Skills

| Component | Strategy | Auto-Merge? |
|-----------|----------|------------|
| YAML metadata | Deep merge, user keys preserved | ✅ Usually |
| Sections | By header (union) | ✅ Usually |
| Examples | Union merge | ✅ Always |
| Content | Line-based 3-way diff | ⚠️ Depends on changes |

**Example**:
```markdown
# BASE: ## Usage
# OURS: ## Usage + ## Examples (user added)
# THEIRS: ## Usage (improved) + ## Advanced
# RESULT: All sections ✅
```

### JSON Configs

| Component | Strategy | Auto-Merge? |
|-----------|----------|------------|
| Keys | Deep recursive merge | ✅ Usually |
| Arrays | Union (combine) | ✅ Usually |
| Values | THEIRS unless user customized | ⚠️ Depends on changes |
| Types | Strict checking | ⚠️ Type mismatch = conflict |

**Example**:
```json
{
  "BASE": {"hooks": ["auth"]},
  "OURS": {"hooks": ["auth"], "custom": {"level": "DEBUG"}},
  "THEIRS": {"hooks": ["auth", "new"], "timeout": 60},
  "RESULT": {"hooks": ["auth", "new"], "custom": {"level": "DEBUG"}, "timeout": 60}
}
```

---

## Conflict Detection Rules

### HIGH Severity (Requires Manual Review)

- ❌ Same function modified by both user and framework
- ❌ Same JSON value changed to different values
- ❌ Framework removes import user is using
- ❌ Markdown section modified by both parties
- ❌ Function signature completely changed

### MEDIUM Severity (Can Auto-Resolve with Confidence)

- ⚠️ User adds section, framework adds different section
- ⚠️ User adds config, framework adds different config
- ⚠️ Reordering of hooks with unknown dependencies

### LOW Severity (Auto-Resolvable)

- ✅ Non-overlapping line changes
- ✅ Framework adds import, user doesn't conflict
- ✅ User adds code below framework code
- ✅ Comment/docstring changes only

---

## Merge Confidence Scoring

```
Confidence = (1.0 - avg_severity) * severity_weights

CRITICAL conflicts → 0.0 confidence
HIGH conflicts → 0.2 confidence
MEDIUM conflicts → 0.6 confidence
LOW conflicts → 0.9 confidence
NO conflicts → 1.0 confidence

AUTO-MERGE if confidence >= 0.95
MANUAL REVIEW if confidence < 0.95
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [x] Core 3-way merge algorithm
- [x] Conflict detection engine
- [x] Conflict marker formatting

### Phase 2: Python Handler (Week 1-2)
- [ ] AST-based Python merge
- [ ] Import union logic
- [ ] Function-level diff

### Phase 3: Markdown Handler (Week 2)
- [ ] YAML frontmatter merge
- [ ] Section-level merge
- [ ] Metadata preservation

### Phase 4: JSON Handler (Week 2)
- [ ] Deep recursive merge
- [ ] Array union semantics
- [ ] Type checking

### Phase 5: Integration (Week 3)
- [ ] Hook update manager
- [ ] Conflict notification system
- [ ] Skill auto-update system

### Phase 6: Testing & Deployment (Week 3-4)
- [ ] Comprehensive test suite
- [ ] Performance benchmarking
- [ ] Production deployment

---

## Usage Examples

### Example 1: Successful Auto-Merge

```python
# Update a hook with user customization

result = await three_way_merge(
    base_content=load_version("v1.0"),
    ours_content=load_current(),
    theirs_content=load_version("v1.1"),
    file_path=".claude/hooks/pre_tool_use.py"
)

if result.status == "success":
    hook_path.write_text(result.merged_content)
    print(f"✅ Merged: {result.message}")
else:
    print(f"⚠️ Conflict: {result.message}")
```

### Example 2: Handling Conflicts

```python
if result.status == "conflict":
    # Create conflict file for user review
    conflict_path = hook_path.with_suffix(".CONFLICT")
    conflict_path.write_text(result.merged_content)

    # Notify user
    print(f"⚠️ Merge conflict in {hook_path}")
    print(f"   Severity: {result.conflicts[0].severity}")
    print(f"   Reason: {result.conflicts[0].reason}")
    print(f"   Review: {conflict_path}")
    print(f"   Confidence: {result.confidence:.1%}")
```

---

## Conflict Marker Format

```python
<<<<<<< MERGED (base → ours → theirs)
def pre_tool_use(tool_name: str, args: Dict) -> Dict:
    """Framework version with type hints."""
    if admin_check():  # THEIRS
        return {"decision": "allow"}
    return {"decision": "block"}

||||||| BASE
def pre_tool_use(tool_name, args):
    return {"decision": "allow"}

=======
def pre_tool_use(tool_name, args):
    """User version with custom logging."""
    logging.info(f"Tool: {tool_name}")  # OURS
    return {"decision": "allow"}

>>>>>>> END MERGED
```

**User Resolution Options**:
1. Accept THEIRS (framework version)
2. Accept OURS (user version)
3. Manually edit to combine both
4. Revert merge

---

## Performance Targets

| Operation | Target | Acceptable |
|-----------|--------|-----------|
| Parse files | <50ms | <100ms |
| Detect conflicts | <50ms | <100ms |
| Generate markers | <100ms | <200ms |
| Complete merge | <200ms | <500ms |
| Large file (10MB) | <1s | <2s |

---

## API Surface

```python
# Main function
async def three_way_merge(
    base_content: str,
    ours_content: str,
    theirs_content: str,
    file_path: Optional[Path] = None,
    options: MergeOptions = None
) -> MergeResult

# Result object
@dataclass
class MergeResult:
    merged_content: Optional[str]    # Merged text
    status: MergeStatus              # success/conflict/error
    conflicts: List[Conflict]        # Details if conflict
    confidence: float                # 0.0-1.0
    message: str                     # Human-readable

# Integration
class HookUpdateManager:
    async def update_hook(
        hook_name: str,
        new_content: str,
        base_version: Optional[str] = None
    ) -> MergeResult
```

---

## Fallback Behavior

| Scenario | Fallback | Action |
|----------|----------|--------|
| **Merge succeeds** | — | Write merged content ✅ |
| **Conflicts detected** | Conflict markers | Create `.CONFLICT` file, notify user |
| **Too many conflicts** | Keep current | Preserve OURS, log warning |
| **Parse error** | Keep current | Preserve OURS, log error |
| **Unknown file type** | Keep current | Skip merge, preserve OURS |

---

## Configuration

```json
{
  "merge": {
    "strategy": "3way",
    "auto_accept_threshold": 0.95,
    "preserve_imports": true,
    "preserve_user_functions": true,
    "backup_before_merge": true,
    "notify_on_conflict": true
  },
  "merge_rules": {
    "python": {
      "ast_aware": true,
      "merge_imports": "union"
    },
    "markdown": {
      "section_merge": true,
      "preserve_user_sections": true
    },
    "json": {
      "deep_merge": true,
      "array_merge": "union"
    }
  }
}
```

---

## Success Criteria

✅ **Algorithm succeeds when:**

1. Auto-mergeable conflicts resolved with >95% confidence
2. User customizations preserved in 100% of cases
3. Framework updates applied when non-conflicting
4. Conflict markers generated in human-readable format
5. Fallback behavior prevents data loss
6. Performance: <1 second for typical files (<100KB)
7. Test coverage: >90% across all handlers

---

## Related Documentation

- [Full Algorithm Specification](./3WAY_MERGE_ALGORITHM.md) - Detailed pseudocode and examples
- [Implementation Guide](./MERGE_IMPLEMENTATION_GUIDE.md) - Code implementation patterns
- [Test Cases](./MERGE_TEST_CASES.md) - Comprehensive test scenarios

---

## Next Steps

1. **Review**: Get team sign-off on algorithm design
2. **Implement**: Follow 6-week implementation plan
3. **Test**: 90%+ coverage, performance benchmarks
4. **Deploy**: Beta testing, production rollout
5. **Monitor**: Track merge success rate, conflicts

---

## Questions & Decisions Needed

- [ ] Should we auto-resolve all LOW severity conflicts? (Current: Yes)
- [ ] What confidence threshold triggers manual review? (Current: 0.95)
- [ ] How long to keep backup files? (Current: Undefined)
- [ ] Should hook ordering be order-sensitive? (Current: Yes)
- [ ] Maximum file size for merge (Current: 10MB)

---

## Glossary

| Term | Definition |
|------|-----------|
| **BASE** | Original framework version (v1.0) |
| **OURS** | Current user-modified version |
| **THEIRS** | New framework version (v1.1) |
| **3-way merge** | Merge algorithm considering BASE, OURS, THEIRS |
| **Conflict** | Incompatible changes between OURS and THEIRS |
| **Confidence** | Score 0.0-1.0 indicating merge safety |
| **Auto-merge** | Merge completed without human review |
| **Marker** | Text indicating conflict location |

---

**Created**: 2024-01-15
**Last Updated**: 2024-01-15
**Status**: Final Specification ✅
