# 3-Way Merge Algorithm for Hook/Skill Updates

**Purpose**: Automatically merge framework updates (base → new version) with user customizations while preserving both.

**Scope**: Python hooks, Markdown skills, and JSON configurations in Stravinsky.

---

## 1. Algorithm Overview

### 1.1 Core Concept

```
     BASE (v1.0)
         |
    ┌────┴────┐
    |         |
  OURS      THEIRS
(User mods) (v1.1 update)
    |         |
    └────┬────┘
         |
      MERGE
         |
    ┌────┴─────────────────────┐
    |                          |
  AUTO-MERGE            CONFLICT DETECTED
  (no changes)          (manual review needed)
    |                          |
  ACCEPT                  RESOLVE
```

### 1.2 Input

Three file versions:
- **BASE**: Original framework version (v1.0)
- **OURS**: User-modified version
- **THEIRS**: New framework version (v1.1)

### 1.3 Output

One of three outcomes:
1. **MERGED**: Clean 3-way merge without conflicts
2. **CONFLICT**: Human-reviewable format with conflict markers
3. **CANNOT_MERGE**: Fallback to manual intervention

---

## 2. Conflict Detection Rules

### 2.1 What Constitutes a Conflict

A **conflict** occurs when:

| Scenario | Detection | Severity |
|----------|-----------|----------|
| **Overlapping Changes** | Same line modified in OURS and THEIRS | HIGH |
| **Function Signature Change** | Parameter count/types differ in THEIRS | HIGH |
| **Import Removal** | OURS uses import, THEIRS removes it | MEDIUM |
| **Hook Ordering** | THEIRS reorders hooks, OURS expects order | MEDIUM |
| **Section Deletion** | OURS has content, THEIRS deletes section | MEDIUM |
| **Configuration Conflict** | OURS sets value, THEIRS sets different value | HIGH |

### 2.2 Non-Conflicts (Auto-Mergeable)

These do NOT create conflicts:

| Scenario | Resolution |
|----------|-----------|
| **Additions in Different Areas** | Both sections kept (union merge) |
| **User Adds Code Below THEIRS** | Keep user additions at end |
| **Framework Adds Import, User Doesn't Use It** | Keep framework import |
| **Framework Adds Function, User Doesn't Touch It** | Keep framework function |
| **Metadata Change (comments, docstrings)** | Keep THEIRS (newer) |

---

## 3. File Type-Specific Merge Rules

### 3.1 Python Hooks (`.claude/hooks/*.py`)

**Structure**:
```python
# Imports section
import sys
from pathlib import Path

# Helper functions
def helper_fn():
    pass

# Main hook function
def pre_tool_use(tool_name, args):
    pass
```

**Merge Strategy**:

| Component | Merge Strategy | Conflict Handling |
|-----------|----------------|-------------------|
| **Imports** | Union merge | Conflict if OURS imports X, THEIRS doesn't (preserve OURS) |
| **Helper functions** | By function name (line-based diff) | Conflict if both modify same function |
| **Main hook function** | Line-based diff with context | Conflict if overlapping changes |
| **Comments/Docstrings** | Keep THEIRS (prefer newer) | No conflict |
| **Shebang line** | Keep THEIRS | No conflict |

**Algorithm**:

```python
def merge_python_hook(base, ours, theirs):
    """Merge Python hook files using AST awareness."""

    # Step 1: Parse all versions into AST
    base_ast = parse_python(base)
    ours_ast = parse_python(ours)
    theirs_ast = parse_python(theirs)

    # Step 2: Extract components
    base_imports = extract_imports(base_ast)
    ours_imports = extract_imports(ours_ast)
    theirs_imports = extract_imports(theirs_ast)

    base_funcs = extract_functions(base_ast)
    ours_funcs = extract_functions(ours_ast)
    theirs_funcs = extract_functions(theirs_ast)

    # Step 3: Merge imports (union of all)
    merged_imports = merge_imports(base_imports, ours_imports, theirs_imports)

    # Step 4: Merge functions
    merged_funcs = {}

    for func_name, func_def in theirs_funcs.items():
        if func_name == 'main' or func_name.startswith('hook_'):
            # Main hook function - use 3-way diff
            if func_name in ours_funcs and func_name in base_funcs:
                merged = three_way_diff(
                    base_funcs[func_name],
                    ours_funcs[func_name],
                    func_def
                )
                if merged.has_conflict:
                    raise ConflictError(f"Conflict in {func_name}")
                merged_funcs[func_name] = merged.text
            else:
                merged_funcs[func_name] = func_def
        else:
            # Helper function - check for modification
            if func_name in ours_funcs:
                # Both have it - check for differences from base
                if is_different(base_funcs.get(func_name), ours_funcs[func_name]):
                    # User modified - conflict if THEIRS also different
                    if is_different(base_funcs.get(func_name), func_def):
                        raise ConflictError(f"Both modified {func_name}")
                    merged_funcs[func_name] = ours_funcs[func_name]
                else:
                    merged_funcs[func_name] = func_def
            else:
                merged_funcs[func_name] = func_def

    # Step 5: Preserve user-added functions
    for func_name, func_def in ours_funcs.items():
        if func_name not in base_funcs and func_name not in theirs_funcs:
            merged_funcs[func_name] = func_def

    # Step 6: Reconstruct file
    return reconstruct_python(merged_imports, merged_funcs)
```

**Examples**:

**Example 1: Add user import (auto-merge)**
```python
# BASE
from pathlib import Path

# OURS (user added logging)
import logging
from pathlib import Path

# THEIRS (framework update)
from pathlib import Path
from typing import Dict

# RESULT
import logging
from pathlib import Path
from typing import Dict
```

**Example 2: User modifies function, framework updates same function (conflict)**
```python
# BASE
def pre_tool_use(tool_name, args):
    if tool_name == "Read":
        return allow()
    return block()

# OURS (user added custom logic)
def pre_tool_use(tool_name, args):
    if tool_name == "Read":
        if user_is_admin():
            return allow()
    return block()

# THEIRS (framework adds support)
def pre_tool_use(tool_name, args):
    if tool_name == "Read":
        if args.get("safe"):
            return allow()
    return block()

# RESULT: CONFLICT
# Conflicting changes at same location
```

---

### 3.2 Markdown Skills (`.claude/commands/**/*.md`)

**Structure**:
```markdown
---
description: Skill description
model: gemini-3-flash
---

# Title

Content...
```

**Merge Strategy**:

| Component | Merge Strategy | Conflict Handling |
|-----------|----------------|-------------------|
| **YAML Frontmatter** | Merge keys (THEIRS overrides unless user has custom key) | Conflict if value types differ |
| **Heading Sections** | By section header (union) | Keep both if different content |
| **Code Examples** | By block (preserve all) | Conflict if same example modified both ways |
| **Usage Instructions** | Line-based diff | Conflict if overlapping edits |

**Algorithm**:

```python
def merge_markdown_skill(base, ours, theirs):
    """Merge Markdown skill files."""

    # Step 1: Parse YAML frontmatter
    base_meta, base_body = parse_markdown(base)
    ours_meta, ours_body = parse_markdown(ours)
    theirs_meta, theirs_body = parse_markdown(theirs)

    # Step 2: Merge metadata
    merged_meta = {}

    for key, value in theirs_meta.items():
        if key in ours_meta:
            if key in base_meta and base_meta[key] != ours_meta[key]:
                # User customized this key
                merged_meta[key] = ours_meta[key]
            else:
                # Check type consistency
                if type(value) != type(ours_meta[key]):
                    raise ConflictError(f"Type mismatch in {key}")
                merged_meta[key] = theirs_meta[key]
        else:
            merged_meta[key] = value

    # User-added keys in OURS
    for key, value in ours_meta.items():
        if key not in theirs_meta:
            merged_meta[key] = value

    # Step 3: Merge body sections
    base_sections = split_by_headers(base_body)
    ours_sections = split_by_headers(ours_body)
    theirs_sections = split_by_headers(theirs_body)

    merged_sections = {}

    # Process THEIRS sections (preferred)
    for header, content in theirs_sections.items():
        if header in ours_sections:
            # Both have this section - check for changes
            base_content = base_sections.get(header, "")

            if is_different(base_content, ours_sections[header]):
                # User modified - use 3-way diff
                merged = three_way_diff(base_content, ours_sections[header], content)
                if merged.has_conflict:
                    raise ConflictError(f"Conflict in section: {header}")
                merged_sections[header] = merged.text
            else:
                # User didn't change - take THEIRS
                merged_sections[header] = content
        else:
            merged_sections[header] = content

    # Preserve user-added sections
    for header, content in ours_sections.items():
        if header not in base_sections and header not in theirs_sections:
            merged_sections[header] = content

    # Step 4: Reconstruct
    return reconstruct_markdown(merged_meta, merged_sections)
```

**Examples**:

**Example 1: Add section (auto-merge)**
```markdown
# BASE
---
description: Original skill
---

## Usage
Use it like this

# OURS (user added section)
---
description: Original skill
---

## Usage
Use it like this

## Examples
- Example 1
- Example 2

# THEIRS (framework enhancement)
---
description: Updated skill
version: 2.0
---

## Usage
Use it like this

# RESULT
---
description: Updated skill
version: 2.0
---

## Usage
Use it like this

## Examples
- Example 1
- Example 2
```

---

### 3.3 JSON Configurations (`.claude/settings.json`)

**Merge Strategy**:

| Component | Merge Strategy | Conflict Handling |
|-----------|----------------|-------------------|
| **Object Keys** | Recursive merge | Conflict if value type differs |
| **Arrays** | Concatenate (union by value) | Conflict if element order matters |
| **Primitive Values** | THEIRS (framework) unless OURS customized | Conflict if both modified same key |
| **Nested Objects** | Recursive application of above | Deep merge with conflict detection |

**Algorithm**:

```python
def merge_json_config(base, ours, theirs):
    """Deep merge JSON configurations."""

    base_obj = json.loads(base)
    ours_obj = json.loads(ours)
    theirs_obj = json.loads(theirs)

    return deep_merge(base_obj, ours_obj, theirs_obj, path="")

def deep_merge(base, ours, theirs, path=""):
    """Recursively merge JSON objects."""

    # Base case: primitives
    if not isinstance(theirs, dict):
        if base != ours:
            # User customized
            if ours != theirs:
                # Both modified - CONFLICT
                raise ConflictError(f"Conflict at {path}: ours={ours}, theirs={theirs}")
        return theirs

    # Recursive case: objects
    result = {}

    # Process THEIRS keys (framework)
    for key, theirs_value in theirs.items():
        base_value = base.get(key)
        ours_value = ours.get(key)

        if isinstance(theirs_value, dict):
            result[key] = deep_merge(
                base_value or {},
                ours_value or {},
                theirs_value,
                path=f"{path}.{key}"
            )
        elif isinstance(theirs_value, list):
            # Arrays: union merge
            result[key] = merge_arrays(base_value or [], ours_value or [], theirs_value)
        else:
            # Primitive
            if ours_value is not None:
                if base_value != ours_value:
                    # User customized - preserve
                    if ours_value != theirs_value:
                        # Both modified - CONFLICT
                        raise ConflictError(
                            f"Conflict at {path}.{key}: "
                            f"ours={ours_value}, theirs={theirs_value}"
                        )
                    result[key] = ours_value
                else:
                    result[key] = theirs_value
            else:
                result[key] = theirs_value

    # Preserve user-added keys
    for key, ours_value in ours.items():
        if key not in base and key not in theirs:
            result[key] = ours_value

    return result

def merge_arrays(base, ours, theirs):
    """Merge JSON arrays (union semantics)."""

    # If all identical, return THEIRS
    if base == ours == theirs:
        return theirs

    # If order-sensitive (hook list), use conflict
    if is_order_sensitive(theirs):
        if base != ours or base != theirs:
            raise ConflictError("Cannot auto-merge order-sensitive array")

    # Otherwise union: base + (ours - base) + (theirs - base)
    result = list(theirs)
    for item in ours:
        if item not in result:
            result.append(item)

    return result
```

**Examples**:

**Example 1: Add configuration (auto-merge)**
```json
# BASE
{
  "hooks": [
    {"name": "pre_tool_use", "enabled": true}
  ]
}

# OURS (user added custom hook)
{
  "hooks": [
    {"name": "pre_tool_use", "enabled": true},
    {"name": "custom_hook", "enabled": true}
  ]
}

# THEIRS (framework adds hook)
{
  "hooks": [
    {"name": "pre_tool_use", "enabled": true},
    {"name": "new_framework_hook", "enabled": false}
  ]
}

# RESULT (union)
{
  "hooks": [
    {"name": "pre_tool_use", "enabled": true},
    {"name": "new_framework_hook", "enabled": false},
    {"name": "custom_hook", "enabled": true}
  ]
}
```

---

## 4. Merge Decision Matrix

### 4.1 Python Hooks

| Base | OURS | THEIRS | Action | Risk |
|------|------|--------|--------|------|
| func A | func A (modified) | func A (different) | CONFLICT | HIGH |
| func A | func A (unmodified) | func A (different) | AUTO-MERGE (THEIRS) | LOW |
| func A | func A (modified) | func A (same) | AUTO-MERGE (OURS) | LOW |
| func A | func A + func B | func A (modified) | THREE-WAY func A, keep B | MEDIUM |
| import X | import X + Y | import X + Z | AUTO-MERGE (union) | LOW |

### 4.2 Markdown Skills

| Base | OURS | THEIRS | Action | Risk |
|------|------|--------|--------|------|
| Section A | Section A (modified) | Section A (different) | CONFLICT | HIGH |
| Section A | Section A (unmodified) | Section A (different) | AUTO-MERGE (THEIRS) | LOW |
| meta: v1 | meta: v1 (user set) | meta: v2 | AUTO-MERGE (THEIRS, if no customization) | MEDIUM |
| meta: v1 | meta: custom-v | meta: v2 | AUTO-MERGE (keep user value) | LOW |

### 4.3 JSON Configs

| Base | OURS | THEIRS | Action | Risk |
|------|------|--------|--------|------|
| {a: 1} | {a: 2} | {a: 3} | CONFLICT | HIGH |
| {a: 1} | {a: 1} | {a: 3} | AUTO-MERGE (THEIRS) | LOW |
| {a: 1, b: 2} | {a: 1, b: 2} | {a: 1, c: 3} | AUTO-MERGE (union) | LOW |

---

## 5. User Customization Preservation

### 5.1 How to Detect User Customization

```python
def is_user_customized(base_content, ours_content):
    """Check if user has modified from base."""

    # Normalize whitespace
    base_norm = normalize(base_content)
    ours_norm = normalize(ours_content)

    if base_norm == ours_norm:
        return False  # Not customized

    # Check if it's just comment changes
    base_no_comments = strip_comments(base_norm)
    ours_no_comments = strip_comments(ours_norm)

    if base_no_comments == ours_no_comments:
        return False  # Only comment changes

    # It's customized
    return True
```

### 5.2 Preservation Strategy

**Rule 1**: If user added code sections → preserve them
```python
# BASE has nothing here
# OURS has custom logging
# THEIRS has nothing
→ Keep user logging (union)
```

**Rule 2**: If user imported something → assume they need it
```python
# BASE doesn't import X
# OURS imports X
# THEIRS doesn't import X
→ Keep import X
```

**Rule 3**: If user modified function but THEIRS has same function unchanged → keep OURS
```python
# BASE: func A
# OURS: func A (user modified)
# THEIRS: func A (same as BASE)
→ Keep OURS version
```

**Rule 4**: If both user and framework modified same section → CONFLICT
```python
# BASE: def hook(): return allow()
# OURS: def hook(): if user_check(): return allow()
# THEIRS: def hook(): if admin(): return deny()
→ CONFLICT (need manual review)
```

---

## 6. Auto-Mergeable vs Manual Review

### 6.1 Auto-Mergeable Patterns

✅ These can be automatically merged:

| Pattern | Example | Confidence |
|---------|---------|-----------|
| **Addition** | OURS adds section, THEIRS unchanged | VERY HIGH |
| **Framework update, no user change** | THEIRS modified, OURS unchanged from BASE | VERY HIGH |
| **Non-overlapping changes** | OURS modifies line 10, THEIRS modifies line 50 | HIGH |
| **Import union** | OURS adds import Y, THEIRS adds import Z | HIGH |
| **Metadata update** | THEIRS updates version/description | MEDIUM |
| **Comment/docstring only** | THEIRS adds documentation | HIGH |

### 6.2 Manual Review Triggers

⚠️ These require human review:

| Pattern | Reason | Severity |
|---------|--------|----------|
| **Overlapping edits** | Same lines modified by both | CRITICAL |
| **Function signature change** | THEIRS adds/removes parameter | HIGH |
| **Behavior reversal** | THEIRS does opposite of OURS intent | HIGH |
| **Hook reordering** | THEIRS changes execution order | HIGH |
| **Import removal** | THEIRS removes import OURS uses | HIGH |
| **Data structure change** | JSON array becomes object | HIGH |

### 6.3 Confidence Levels

```python
def calculate_merge_confidence(base, ours, theirs):
    """Determine confidence level for auto-merge."""

    # VERY HIGH (>95%)
    if not is_user_customized(base, ours):
        return 0.99, "Framework update, no user changes"

    if no_overlap(ours, theirs):
        return 0.95, "Non-overlapping changes"

    # HIGH (85-95%)
    if is_import_section_only(ours, theirs):
        return 0.90, "Only import changes"

    # MEDIUM (70-85%)
    if has_minor_conflicts(ours, theirs):
        return 0.75, "Minor conflicts, likely resolvable"

    # LOW (<70%)
    return 0.0, "Significant conflicts, needs review"
```

---

## 7. Hook Ordering & Dependencies

### 7.1 Hook Execution Order Matters

Hooks are executed in a specific order. Reordering can break behavior:

```yaml
hooks:
  - name: auth_check        # Must run first
  - name: permission_check  # Depends on auth_check
  - name: logging          # Can run anywhere
```

### 7.2 Handling Hook Reordering

```python
def merge_hook_list(base_hooks, ours_hooks, theirs_hooks):
    """Merge hook lists while preserving order semantics."""

    # Identify which hooks are user-added
    user_added = [h for h in ours_hooks if h not in base_hooks]
    framework_changed = [h for h in theirs_hooks if h not in base_hooks or
                         base_hooks.index(h) != theirs_hooks.index(h)]

    if framework_changed and user_added:
        # Potential ordering issue
        raise ConflictError("Hook order conflict - cannot auto-merge")

    # If no user additions, take THEIRS ordering
    if not user_added:
        return theirs_hooks

    # Otherwise: THEIRS ordering + user_added at end
    result = list(theirs_hooks)
    for hook in user_added:
        if hook not in result:
            result.append(hook)

    return result
```

### 7.3 Dependency Tracking

```python
# In .claude/hooks/dependencies.json
{
  "permission_check": {
    "depends_on": ["auth_check"],
    "required_imports": ["auth_module"],
    "min_version": "1.0"
  }
}
```

---

## 8. Fallback Behavior

### 8.1 When 3-Way Merge Fails

| Scenario | Fallback | Action |
|----------|----------|--------|
| **Too many conflicts** | Manual review | Create `.CONFLICT` marker file |
| **Parse error** | Keep OURS | User version preserved, log error |
| **Circular dependency** | Keep BASE | Revert to stable version |
| **Unknown file type** | Keep OURS | Skip merge, preserve user version |

### 8.2 Conflict Marker Format

```python
# Python
<<<<<<< MERGED (base→ours→theirs)
def pre_tool_use(tool_name, args):
    if user_check():  # OURS
        return allow()
||||||| BASE
def pre_tool_use(tool_name, args):
    return allow()
=======
def pre_tool_use(tool_name, args):  # THEIRS
    if admin_check():
        return allow()
>>>>>>> END MERGED
```

```markdown
# Markdown
<<<<<<< MERGED
## Usage (OURS)
Use this way

||||||| BASE
## Usage
(none)

=======
## Usage (THEIRS)
Use that way
>>>>>>> END MERGED
```

---

## 9. Full Merge Algorithm (Pseudocode)

```python
def three_way_merge(base_file, ours_file, theirs_file):
    """
    Main 3-way merge algorithm.

    Returns: (merged_content, status, conflicts)
    - status: "success", "conflict", "error"
    - conflicts: List of conflict details if status="conflict"
    """

    # Step 1: Validate inputs
    if not is_valid_file(base_file) or not is_valid_file(ours_file) or not is_valid_file(theirs_file):
        return None, "error", ["Invalid input files"]

    # Step 2: Detect file type
    file_type = detect_file_type(base_file)

    # Step 3: Route to type-specific merger
    try:
        if file_type == "python":
            result = merge_python_hook(base_file, ours_file, theirs_file)
        elif file_type == "markdown":
            result = merge_markdown_skill(base_file, ours_file, theirs_file)
        elif file_type == "json":
            result = merge_json_config(base_file, ours_file, theirs_file)
        else:
            return None, "error", ["Unknown file type"]

    except ConflictError as e:
        # Step 4: Handle conflicts
        conflicts = extract_conflicts(base_file, ours_file, theirs_file)
        conflict_markers = insert_conflict_markers(
            base_file, ours_file, theirs_file, conflicts
        )
        return conflict_markers, "conflict", conflicts

    except Exception as e:
        return ours_file, "error", [str(e)]

    # Step 5: Validate result
    if not validate_merged(result, file_type):
        return ours_file, "error", ["Validation failed"]

    return result, "success", []


def merge_workflow(hook_path, base_version, new_version):
    """
    Complete merge workflow for updating a hook.

    1. Load versions
    2. Attempt merge
    3. Handle conflicts or accept result
    4. Backup original
    5. Write merged version
    """

    # Step 1: Load versions
    base = load_version(hook_path, base_version)
    ours = load_current(hook_path)
    theirs = load_version(hook_path, new_version)

    # Step 2: Merge
    merged, status, conflicts = three_way_merge(base, ours, theirs)

    # Step 3: Handle result
    if status == "success":
        # Auto-accept
        backup_file(hook_path, ours)
        write_file(hook_path, merged)
        log_merge_success(hook_path, base_version, new_version)
        return "merged"

    elif status == "conflict":
        # Create conflict file for review
        conflict_file = f"{hook_path}.CONFLICT"
        write_file(conflict_file, merged)
        notify_user(f"Merge conflict in {hook_path} - review {conflict_file}")
        return "conflict"

    else:
        # Error - keep current
        log_merge_error(hook_path, conflicts)
        return "error"
```

---

## 10. Implementation Checklist

- [ ] **Phase 1: Foundation**
  - [ ] Implement `three_way_merge()` core algorithm
  - [ ] Implement conflict detection for each file type
  - [ ] Implement conflict marker insertion

- [ ] **Phase 2: Python Hooks**
  - [ ] AST-based merge for Python files
  - [ ] Import union logic
  - [ ] Function-level diff and merge

- [ ] **Phase 3: Markdown Skills**
  - [ ] YAML frontmatter merge
  - [ ] Section-level merge by header
  - [ ] Metadata preservation

- [ ] **Phase 4: JSON Configs**
  - [ ] Deep recursive merge
  - [ ] Array union semantics
  - [ ] Type checking and validation

- [ ] **Phase 5: Integration**
  - [ ] Hook update mechanism
  - [ ] Skill auto-update system
  - [ ] Conflict notification system

- [ ] **Phase 6: Testing**
  - [ ] Unit tests for each merge function
  - [ ] Integration tests with real hooks
  - [ ] Edge case testing

---

## 11. Example: Complete Merge Scenario

### Scenario: Updating `pre_tool_use.py` Hook

**BASE (v1.0)**:
```python
def pre_tool_use(tool_name, args):
    """Allow all tools."""
    if tool_name in ["Write", "Edit"]:
        return {"decision": "allow"}
    return {"decision": "block"}
```

**OURS (User Modified)**:
```python
import logging

def pre_tool_use(tool_name, args):
    """Allow all tools, with logging."""
    logging.info(f"Tool used: {tool_name}")
    if tool_name in ["Write", "Edit"]:
        return {"decision": "allow"}
    return {"decision": "block"}
```

**THEIRS (v1.1 - Framework Update)**:
```python
from typing import Dict

def pre_tool_use(tool_name: str, args: Dict) -> Dict:
    """Allow safe tools, block dangerous ones."""
    SAFE_TOOLS = ["Write", "Edit", "Bash"]
    if tool_name in SAFE_TOOLS:
        return {"decision": "allow"}
    return {"decision": "block"}
```

**Merge Analysis**:

1. **Imports**: Union → `import logging` + `from typing import Dict`
2. **Function signature**: THEIRS has type hints, OURS doesn't
3. **Function body**: Overlapping changes

   | Line | BASE | OURS | THEIRS |
   |------|------|------|--------|
   | 1-2 | (docstring) | (docstring) | (docstring) |
   | 3 | — | logging.info(...) | SAFE_TOOLS = [...] |
   | 4 | if tool_name in [...] | if tool_name in [...] | if tool_name in SAFE_TOOLS: |

4. **Conflict**: Line 4 has different logic (added logging vs. SAFE_TOOLS)

**Result: CONFLICT**

```python
<<<<<<< MERGED (v1.0→user→v1.1)
import logging
from typing import Dict

def pre_tool_use(tool_name: str, args: Dict) -> Dict:
    """Allow safe tools."""
    logging.info(f"Tool used: {tool_name}")  # OURS

    SAFE_TOOLS = ["Write", "Edit", "Bash"]  # THEIRS
    if tool_name in SAFE_TOOLS:
||||||| BASE
def pre_tool_use(tool_name, args):
    """Allow all tools."""
    if tool_name in ["Write", "Edit"]:
=======
def pre_tool_use(tool_name: str, args: Dict) -> Dict:
    """Allow safe tools, block dangerous ones."""
    SAFE_TOOLS = ["Write", "Edit", "Bash"]
    if tool_name in SAFE_TOOLS:
>>>>>>> END MERGED
        return {"decision": "allow"}
    return {"decision": "block"}
```

**Resolution**: User reviews and decides:
- Option A: Keep logging + use SAFE_TOOLS
- Option B: Accept framework update, remove logging
- Option C: Custom resolution

---

## 12. Edge Cases & Handling

### 12.1 Empty Files

```
BASE: (empty)
OURS: (user added content)
THEIRS: (framework added content)
→ RESULT: Union of OURS + THEIRS
```

### 12.2 Deleted Files

```
BASE: (has content)
OURS: (user kept it)
THEIRS: (framework deleted it)
→ RESULT: CONFLICT (deletion + retention)
```

### 12.3 Binary or Non-Text Files

```
→ RESULT: Cannot merge, keep OURS
```

### 12.4 Encoding Mismatches

```
BASE: UTF-8
OURS: UTF-8 (with user edits)
THEIRS: UTF-16 (framework resave)
→ RESULT: Convert to UTF-8, attempt merge
```

---

## 13. Configuration

### 13.1 Merge Settings

```json
{
  "merge": {
    "strategy": "3way",
    "conflict_handling": "preserve_user",
    "auto_accept_threshold": 0.95,
    "preserve_imports": true,
    "preserve_user_functions": true,
    "backup_before_merge": true,
    "notify_on_conflict": true
  }
}
```

### 13.2 Per-File Type Settings

```json
{
  "merge_rules": {
    "python": {
      "ast_aware": true,
      "preserve_comments": false,
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

## 14. Success Criteria

✅ Algorithm succeeds when:

1. **Auto-mergeable conflicts** resolved with 95%+ confidence
2. **User customizations** preserved in 100% of cases
3. **Framework updates** applied when non-conflicting
4. **Conflict markers** generated in human-readable format
5. **Fallback behavior** prevents data loss
6. **Performance**: Merge completes in <1 second

---

## References

- 3-way merge concept: Git merge algorithm
- Conflict detection: Line-based + AST-aware
- User intent: Preserve customizations by default
- Safety: Always backup before merge
