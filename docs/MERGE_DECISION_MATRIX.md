# 3-Way Merge Decision Matrix

**Quick reference for merge decisions across all file types.**

---

## 1. Python Hooks Decision Matrix

### Imports Resolution

```
BASE IMPORT          OURS IMPORT          THEIRS IMPORT        DECISION         SEVERITY
─────────────────────────────────────────────────────────────────────────────────────────
✓ import X           ✓ import X           ✓ import X           KEEP X           NONE
✓ import X           ✓ import X           ✗ import X           KEEP X           LOW
✓ import X           ✗ import X           ✓ import X           KEEP X           LOW
✗ -                  ✓ import X           ✗ -                  KEEP X           LOW
✗ -                  ✓ import X           ✓ import Y           KEEP BOTH        LOW
✓ import X           ✓ import X + Y       ✓ import X + Z       KEEP X+Y+Z       LOW
✓ import X           ✓ import X as x1     ✓ import X as x2     CONFLICT         HIGH
✓ import X           ✗ import X           ✗ import X           REMOVE X         LOW
```

**Rule**: Union merge all imports. Conflict only if same import aliased differently.

---

### Function Changes Resolution

```
FUNC IN BASE         FUNC IN OURS         FUNC IN THEIRS       ACTION           SEVERITY
──────────────────────────────────────────────────────────────────────────────────────────
✓ func A             ✓ func A (SAME)      ✓ func A (SAME)      KEEP A           NONE
✓ func A             ✓ func A (SAME)      ✓ func A (DIFF)      USE THEIRS       LOW
✓ func A             ✓ func A (DIFF)      ✓ func A (SAME)      KEEP OURS        LOW
✓ func A             ✓ func A (DIFF1)     ✓ func A (DIFF2)     CONFLICT         HIGH
✓ func A             ✗ func A             ✓ func A (SAME)      REMOVE A         MEDIUM
✓ func A             ✗ func A             ✓ func A (DIFF)      CONFLICT         HIGH
✓ func A             ✗ func A             ✗ func A             REMOVE A         LOW
✗ -                  ✓ func B (NEW)       ✗ -                  KEEP B           LOW
✗ -                  ✓ func B (NEW)       ✓ func C (NEW)       KEEP BOTH        LOW
```

**Rule**: 3-way diff on functions. User mods preserved. Overlapping changes = conflict.

---

### Python File Merge Flowchart

```
START: Merge Python Files
    ↓
[Parse all 3 versions]
    ↓
[Extract imports]
    ├→ Union merge all imports
    └→ No conflicts expected
    ↓
[Extract functions by name]
    ├→ For each function in THEIRS:
    │   ├→ If OURS has modified & THEIRS modified differently → CONFLICT
    │   ├→ If OURS has modified & THEIRS same as BASE → KEEP OURS
    │   ├→ If OURS hasn't modified → USE THEIRS
    │   └→ Add to merged
    ├→ For each function in OURS not in THEIRS → ADD to merged
    └→ Done
    ↓
[Reconstruct file]
    ├→ Imports at top
    ├→ All functions
    └→ Preserve order
    ↓
[Conflicts found?]
    ├→ YES: Return CONFLICT status, generate markers
    └→ NO: Return merged content, SUCCESS status
    ↓
END
```

---

## 2. Markdown Skills Decision Matrix

### Metadata (YAML Frontmatter)

```
KEY IN BASE          VALUE IN OURS        VALUE IN THEIRS      ACTION           SEVERITY
──────────────────────────────────────────────────────────────────────────────────────────
✓ v: 1.0            ✓ v: 1.0            ✓ v: 1.1             USE THEIRS       LOW
✓ v: 1.0            ✓ v: 1.0            ✓ v: 1.1 (int)       USE THEIRS       LOW
✓ v: 1.0            ✓ v: 1.5 (custom)   ✓ v: 1.1             CONFLICT         MEDIUM
✓ desc: "..."       ✓ desc: "..."       ✓ desc: "..." (new)  USE THEIRS       LOW
✗ -                 ✓ custom: val       ✗ -                  KEEP custom      LOW
✗ -                 ✓ key1: val         ✓ key2: val          KEEP BOTH        LOW
✓ v: 1.0            ✓ v: "v1"           ✓ v: 1.1             CONFLICT (type)  HIGH
```

**Rule**: THEIRS overrides unless user customized. Type mismatches = conflict.

---

### Content Sections

```
SECTION HEADER       OURS HAS IT          THEIRS HAS IT        ACTION           SEVERITY
──────────────────────────────────────────────────────────────────────────────────────────
# Usage             ✓ SAME               ✓ SAME               KEEP             NONE
# Usage             ✓ SAME               ✓ DIFF               USE THEIRS       LOW
# Usage             ✓ DIFF (better)      ✓ DIFF (other)       CONFLICT         HIGH
# Examples          ✓ YES                ✗ NO                 KEEP             LOW
# Examples          ✓ YES                ✓ YES (diff)         CONFLICT         MEDIUM
# Examples          ✗ NO                 ✓ YES                ADD              LOW
# Custom Workflow   ✓ YES                ✗ NO                 KEEP             LOW
# Custom Workflow   ✓ YES                ✓ YES (same)         KEEP             LOW
```

**Rule**: Keep all unique sections. Overlapping content changes = conflict. User sections preserved.

---

### Markdown File Merge Flowchart

```
START: Merge Markdown Files
    ↓
[Parse frontmatter and body separately]
    ├→ Extract YAML
    └→ Extract body sections by ## header
    ↓
[Merge metadata (YAML)]
    ├→ For each key in THEIRS:
    │   ├→ If user customized (OURS diff from BASE)
    │   │   ├→ If type mismatch → CONFLICT
    │   │   └→ Keep OURS value
    │   └→ Otherwise use THEIRS
    ├→ For each key in OURS not in BASE or THEIRS → KEEP
    └→ Generate merged metadata
    ↓
[Merge body sections by header]
    ├→ For each section in THEIRS:
    │   ├→ If OURS has same section:
    │   │   ├→ 3-way line diff
    │   │   ├→ If conflicts → CONFLICT marker
    │   │   └→ Use result (merged or conflict)
    │   └→ Otherwise use THEIRS
    ├→ For each section in OURS not in BASE or THEIRS → KEEP
    └→ Generate merged body
    ↓
[Reconstruct file]
    ├→ YAML frontmatter
    ├→ All sections in order
    └→ Preserve hierarchy
    ↓
[Conflicts?]
    ├→ YES: Return CONFLICT with markers
    └→ NO: Return merged, SUCCESS
    ↓
END
```

---

## 3. JSON Config Decision Matrix

### Simple Keys

```
BASE KEY             OURS VALUE           THEIRS VALUE         ACTION           SEVERITY
──────────────────────────────────────────────────────────────────────────────────────────
✓ v: 1.0            ✓ v: 1.0             ✓ v: 1.1             USE THEIRS       LOW
✓ v: 1.0            ✓ v: 1.0             ✓ v: 1.1 (type ok)   USE THEIRS       LOW
✓ v: 1.0            ✓ v: 1.5             ✓ v: 1.1             CONFLICT         HIGH
✓ v: 1.0            ✓ v: 1.0             ✗ v: -               REMOVE v         MEDIUM
✓ v: 1.0            ✗ v: -               ✓ v: 1.1             USE THEIRS       LOW
✗ -                 ✓ custom: 123        ✗ -                  KEEP custom      LOW
✓ timeout: 30       ✓ timeout: 60        ✓ timeout: "30"      CONFLICT (type)  HIGH
```

**Rule**: THEIRS unless user customized. Type mismatches = conflict. User keys preserved.

---

### Nested Objects

```
NESTED OBJ           OURS STATE           THEIRS STATE         ACTION           SEVERITY
──────────────────────────────────────────────────────────────────────────────────────────
config.db.host       "localhost"          "localhost"          KEEP             NONE
config.db.host       "localhost"          "db.example.com"     USE THEIRS       LOW
config.db.host       "custom.local"       "db.example.com"     CONFLICT         HIGH
config.db.host       "localhost"          (removed)            REMOVE           MEDIUM
config.db.custom.*   {"x": 1}             (not present)        KEEP             LOW
config.db.*          {...}                {...different}       DEEP MERGE       DEPENDS
```

**Rule**: Recursive merge. Deep merge nested objects. Leaf value conflicts trigger HIGH severity.

---

### Arrays

```
BASE ARRAY           OURS ARRAY           THEIRS ARRAY         ACTION           SEVERITY
──────────────────────────────────────────────────────────────────────────────────────────
[A, B]               [A, B]               [A, B]               KEEP             NONE
[A, B]               [A, B]               [A, B, C]            ADD C            LOW
[A, B]               [A, B, X]            [A, B, C]            UNION (X+C)      LOW
[A, B]               [B, A]               [A, B]               USE THEIRS (order) MEDIUM
[A, B]               [A, C]               [A, B, D]            CONFLICT (B vs C) HIGH
[A, B]               [A]                  [A, B]               USE THEIRS       LOW
[A, B]               [A, B]               [A]                  REMOVE B         MEDIUM
```

**Rule**: Union semantics (combine unique items). Order conflicts trigger MEDIUM/HIGH severity.

---

### JSON Merge Flowchart

```
START: Merge JSON Objects
    ↓
[Parse all 3 JSON objects]
    ↓
FUNCTION: deep_merge(base, ours, theirs, path)
    ├→ Base case: theirs is primitive
    │   ├→ If base != ours: user customized
    │   │   ├→ If ours != theirs: CONFLICT
    │   │   └→ Return CONFLICT / ours
    │   └→ Return theirs
    ├→ Recursive case: theirs is object
    │   ├→ For each key in theirs:
    │   │   ├→ If value is object: recurse deep_merge
    │   │   ├→ If value is array: merge_arrays
    │   │   └→ If primitive: same as above
    │   ├→ For each key in ours not in base or theirs:
    │   │   └→ Add to result (user custom)
    │   └→ Return merged object
    ↓
[Collect all conflicts]
    ↓
[Convert to JSON with indentation]
    ↓
[Return merged content + conflicts]
    ↓
END
```

---

## 4. Universal Decision Flowchart

```
┌─ START ─┐
    ↓
[Detect file type]
    ├→ .py → Python handler
    ├→ .md → Markdown handler
    ├→ .json → JSON handler
    └→ else → Text handler
    ↓
[Parse all 3 versions]
    ├→ Success → Continue
    └→ Error → Return ERROR (keep OURS)
    ↓
[Extract components]
    ├→ Python: imports + functions
    ├→ Markdown: metadata + sections
    ├→ JSON: recursive keys/arrays
    └→ Text: line-based
    ↓
[Apply merge algorithm]
    ├→ For each component:
    │   ├→ Check for conflicts
    │   ├→ Determine action (use THEIRS/OURS/MERGE/CONFLICT)
    │   └→ Collect results
    ↓
[Collect all conflicts]
    ↓
[Classify conflicts by severity]
    ├→ CRITICAL (>0): Auto-fail? No, check count
    ├→ HIGH (0.2): Needs review
    ├→ MEDIUM (0.6): May auto-resolve
    └→ LOW (0.9): Auto-resolvable
    ↓
[Calculate confidence score]
    ├→ 0 conflicts → 1.0 (100%)
    ├→ Only LOW conflicts → 0.9 (90%)
    ├→ MEDIUM conflicts → 0.6 (60%)
    ├→ HIGH conflicts → 0.2 (20%)
    └→ CRITICAL conflicts → 0.0 (0%)
    ↓
[Confidence > 0.95?]
    ├─ YES → AUTO-MERGE (return SUCCESS)
    └─ NO → Generate conflict markers (return CONFLICT)
    ↓
[Reconstruct merged file]
    ├→ Python: imports + functions
    ├→ Markdown: metadata + sections
    ├→ JSON: merged object
    └→ Text: with conflict markers
    ↓
[Return MergeResult]
    ├→ merged_content
    ├→ status (success/conflict/error)
    ├→ conflicts
    ├→ confidence
    └→ message
    ↓
END
```

---

## 5. Conflict Marker Examples

### Python Conflict Marker

```python
<<<<<<< MERGED (base→ours→theirs)
def pre_tool_use(tool_name: str, args: Dict) -> Dict:
    """THEIRS: Added type hints."""
    if admin_check():
        return {"decision": "allow"}
    return {"decision": "block"}

||||||| BASE
def pre_tool_use(tool_name, args):
    return {"decision": "allow"}

=======
def pre_tool_use(tool_name, args):
    """OURS: Added custom check."""
    if user_is_admin():
        return {"decision": "allow"}
    return {"decision": "block"}

>>>>>>> END MERGED
```

### Markdown Conflict Marker

```markdown
<<<<<<< MERGED
## Usage (THEIRS)
Use this tool with:
```bash
/skill --option value
```

||||||| BASE
## Usage
Run the command.

=======
## Usage (OURS)
Custom usage:
1. Check preconditions
2. Run skill
3. Verify output

>>>>>>> END MERGED
```

### JSON Conflict Marker

```json
{
  "version": "<<<<<<< MERGED (ours=1.5 THEIRS=1.1)",
  "version_ours": "1.5",
  "version_base": "1.0",
  "version_theirs": "1.1",
  "||||||||_note": "User customized version to 1.5, framework wants 1.1",
  "conflict_resolved_as": "MANUAL_REVIEW_NEEDED"
}
```

---

## 6. Severity Reference

| Level | Score | Examples | Action |
|-------|-------|----------|--------|
| **CRITICAL** | 0.0 | Parse errors, missing data | Manual fix required |
| **HIGH** | 0.2 | Function changes, value conflicts | Requires review |
| **MEDIUM** | 0.6 | Metadata conflicts, minor overlaps | Can auto-resolve with caution |
| **LOW** | 0.9 | Non-overlapping changes, comments | Auto-resolvable |
| **NONE** | 1.0 | No conflicts | Auto-merge |

---

## 7. Resolution Strategy by Severity

| Severity | User Modified | Framework Modified | Action | Result |
|----------|---------------|-------------------|--------|--------|
| NONE | No | No | Keep | ✅ MERGE |
| NONE | No | Yes | Use THEIRS | ✅ MERGE |
| NONE | Yes | No | Keep OURS | ✅ MERGE |
| LOW | No | Yes | Use THEIRS | ✅ MERGE |
| LOW | Yes | No | Keep OURS | ✅ MERGE |
| MEDIUM | Yes | Yes | Heuristic | ⚠️ DEPENDS |
| HIGH | Yes | Yes | Generate markers | ❌ CONFLICT |
| CRITICAL | Any | Any | Keep OURS | ❌ ERROR |

---

## 8. Quick Decision Guide

**"Should I auto-merge this?"**

```
1. Is there a conflict?
   NO  → Auto-merge ✅
   YES → Go to step 2

2. Is it HIGH or CRITICAL severity?
   YES → Manual review ❌
   NO  → Go to step 3

3. Is confidence > 95%?
   YES → Auto-merge ✅
   NO  → Manual review ❌
```

---

## 9. Checklists

### Pre-Merge Checklist
- [ ] All 3 versions parsed successfully
- [ ] File type detected correctly
- [ ] Components extracted completely
- [ ] No encoding issues

### Post-Merge Checklist
- [ ] Merged content valid for file type
- [ ] No data loss from BASE or OURS
- [ ] Conflicts properly marked (if any)
- [ ] Confidence score calculated
- [ ] Result verified

### Conflict Resolution Checklist
- [ ] Understand what changed in each version
- [ ] Understand why conflict occurred
- [ ] Choose resolution (THEIRS/OURS/MANUAL)
- [ ] Test merged result
- [ ] Verify no regression

---

## 10. Performance Targets by Decision Path

| Decision Path | Target | Acceptable |
|---------------|--------|-----------|
| No conflicts | <50ms | <100ms |
| Detected conflict | <100ms | <200ms |
| Generated markers | <200ms | <500ms |
| Large file (10MB) | <1s | <2s |

---

**Use this matrix as reference during merge implementation and conflict resolution.**
