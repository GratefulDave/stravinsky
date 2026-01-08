# 3-Way Merge Test Cases & Examples

Comprehensive test cases for validating the 3-way merge algorithm implementation.

---

## Test Suite Organization

```
tests/merge/
├── test_python_merge.py       # Python hook merge tests
├── test_markdown_merge.py     # Markdown skill merge tests
├── test_json_merge.py         # JSON config merge tests
├── test_conflict_detection.py # Conflict detection tests
├── fixtures/                  # Test data files
│   ├── python/
│   ├── markdown/
│   └── json/
└── conftest.py               # Pytest fixtures
```

---

## 1. Python Hook Merge Tests

### Test 1.1: No Conflict - Framework Update Only

**Scenario**: Framework improves type hints, user hasn't modified

```python
@pytest.mark.asyncio
async def test_python_no_user_change():
    """User didn't modify, framework added type hints."""
    base = """
def pre_tool_use(tool_name, args):
    if tool_name == "Read":
        return {"decision": "allow"}
    return {"decision": "block"}
"""

    ours = base  # User unchanged

    theirs = """
from typing import Dict

def pre_tool_use(tool_name: str, args: Dict) -> Dict:
    if tool_name == "Read":
        return {"decision": "allow"}
    return {"decision": "block"}
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "success"
    assert "from typing import Dict" in result.merged_content
    assert "tool_name: str" in result.merged_content
    assert len(result.conflicts) == 0
```

**Expected**: ✅ Auto-merge, accept framework type hints

---

### Test 1.2: User Import Preservation

**Scenario**: User added import, framework added different import

```python
@pytest.mark.asyncio
async def test_python_import_union():
    """Union merge of imports from both user and framework."""
    base = """from pathlib import Path"""

    ours = """
import logging
from pathlib import Path
"""

    theirs = """
from pathlib import Path
from typing import Dict, Optional
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "success"
    assert "import logging" in result.merged_content
    assert "from typing import Dict, Optional" in result.merged_content
    assert len(result.conflicts) == 0
```

**Expected**: ✅ Union merge: logging + Path + Dict, Optional

---

### Test 1.3: Function Modification Conflict

**Scenario**: Both user and framework modified same function

```python
@pytest.mark.asyncio
async def test_python_function_conflict():
    """Both user and framework modified same function."""
    base = """
def pre_tool_use(tool_name, args):
    return {"decision": "allow"}
"""

    ours = """
def pre_tool_use(tool_name, args):
    if user_is_admin():
        return {"decision": "allow"}
    return {"decision": "block"}
"""

    theirs = """
def pre_tool_use(tool_name, args):
    SAFE_TOOLS = ["Write", "Edit", "Bash"]
    if tool_name in SAFE_TOOLS:
        return {"decision": "allow"}
    return {"decision": "block"}
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "conflict"
    assert len(result.conflicts) == 1
    assert result.conflicts[0].severity == ConflictSeverity.HIGH
```

**Expected**: ⚠️ Conflict - require manual review

---

### Test 1.4: User Function Addition

**Scenario**: User added new helper function, framework unchanged

```python
@pytest.mark.asyncio
async def test_python_user_added_function():
    """User added custom helper function."""
    base = """
def pre_tool_use(tool_name, args):
    return {"decision": "allow"}
"""

    ours = """
def pre_tool_use(tool_name, args):
    return {"decision": "allow"}

def is_trusted_source(args):
    return args.get("source") == "internal"
"""

    theirs = """
def pre_tool_use(tool_name, args):
    logging.info(f"Tool: {tool_name}")
    return {"decision": "allow"}
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "success"
    assert "is_trusted_source" in result.merged_content
    assert "logging.info" in result.merged_content
```

**Expected**: ✅ Auto-merge - keep user function + framework update

---

### Test 1.5: Import Removal Conflict

**Scenario**: User uses import, framework removes it

```python
@pytest.mark.asyncio
async def test_python_import_removal_conflict():
    """User imports module, framework removes import."""
    base = """
from auth_module import check_admin
"""

    ours = """
from auth_module import check_admin

def verify_access():
    return check_admin()
"""

    theirs = """
# auth_module removed in v2
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "conflict"
    assert "import removal" in result.conflicts[0].reason.lower()
```

**Expected**: ⚠️ Conflict - user still needs the import

---

## 2. Markdown Skill Merge Tests

### Test 2.1: No Conflict - Version Update

**Scenario**: Framework updates version, user hasn't modified

```python
@pytest.mark.asyncio
async def test_markdown_version_update():
    """Framework updates skill version."""
    base = """---
description: Research librarian
version: 1.0
---

# Dewey

Research documentation.
"""

    ours = base

    theirs = """---
description: Research librarian
version: 1.1
updated: 2024-01-15
---

# Dewey

Research documentation.

## New Features
- Better search results
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "success"
    assert 'version: 1.1' in result.merged_content
    assert "New Features" in result.merged_content
```

**Expected**: ✅ Auto-merge - accept framework version update

---

### Test 2.2: User Added Section Preserved

**Scenario**: User added custom section, framework added different section

```python
@pytest.mark.asyncio
async def test_markdown_custom_section_preserved():
    """User's custom section should be preserved."""
    base = """---
description: Original
---

# Title

Content here.
"""

    ours = """---
description: Original
---

# Title

Content here.

## Custom Workflow
My special process:
1. Step 1
2. Step 2
"""

    theirs = """---
description: Updated
---

# Title

Content here.

## Advanced Usage
Technical details here.
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "success"
    assert "## Custom Workflow" in result.merged_content
    assert "## Advanced Usage" in result.merged_content
```

**Expected**: ✅ Union merge - both sections kept

---

### Test 2.3: Section Modification Conflict

**Scenario**: Both user and framework modified same section

```python
@pytest.mark.asyncio
async def test_markdown_section_conflict():
    """Same section modified by both user and framework."""
    base = """---
description: Skill
---

# Usage

Run the command.
"""

    ours = """---
description: Skill
---

# Usage

Run the command:
```bash
/skill argument
```

Then wait for results.
"""

    theirs = """---
description: Skill
---

# Usage

To use this skill, execute:
```bash
/skill [options]
```

See examples below.
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "conflict"
    assert "section conflict" in result.conflicts[0].reason.lower()
```

**Expected**: ⚠️ Conflict - overlapping edits

---

### Test 2.4: Metadata Type Mismatch

**Scenario**: User and framework set metadata key to different types

```python
@pytest.mark.asyncio
async def test_markdown_metadata_type_conflict():
    """Metadata value type conflict."""
    base = """---
timeout: 30
---
Content
"""

    ours = """---
timeout: "30 seconds"
---
Content
"""

    theirs = """---
timeout: 30
---
Content
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "conflict"
    assert "type mismatch" in result.conflicts[0].reason.lower()
```

**Expected**: ⚠️ Conflict - type mismatch

---

## 3. JSON Config Merge Tests

### Test 3.1: No Conflict - New Keys Added

**Scenario**: Framework adds new config keys, user hasn't modified base

```python
@pytest.mark.asyncio
async def test_json_new_keys():
    """Framework adds new configuration keys."""
    base = """
{
  "hooks": ["pre_tool_use"],
  "version": "1.0"
}
"""

    ours = base

    theirs = """
{
  "hooks": ["pre_tool_use"],
  "version": "1.1",
  "experimental": true,
  "timeout": 30
}
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "success"
    assert json.loads(result.merged_content)["version"] == "1.1"
    assert json.loads(result.merged_content)["experimental"] is True
```

**Expected**: ✅ Auto-merge - add new keys

---

### Test 3.2: User Custom Config Preserved

**Scenario**: User added custom configuration, framework added different config

```python
@pytest.mark.asyncio
async def test_json_user_config_preserved():
    """User's custom configuration should be preserved."""
    base = """
{
  "hooks": {
    "enabled": ["pre_tool_use"]
  }
}
"""

    ours = """
{
  "hooks": {
    "enabled": ["pre_tool_use"]
  },
  "custom_logging": {
    "level": "DEBUG",
    "file": "/tmp/debug.log"
  }
}
"""

    theirs = """
{
  "hooks": {
    "enabled": ["pre_tool_use"],
    "order": ["auth", "validation", "execution"]
  },
  "timeout": 60
}
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "success"
    merged = json.loads(result.merged_content)

    assert "custom_logging" in merged
    assert merged["custom_logging"]["level"] == "DEBUG"
    assert "timeout" in merged
    assert merged["timeout"] == 60
```

**Expected**: ✅ Deep merge - user config + framework updates

---

### Test 3.3: Array Union Merge

**Scenario**: Framework and user both add to hook array

```python
@pytest.mark.asyncio
async def test_json_array_union():
    """Arrays merged using union semantics."""
    base = """
{
  "hooks": ["pre_tool_use", "post_tool_use"]
}
"""

    ours = """
{
  "hooks": ["pre_tool_use", "post_tool_use", "custom_hook"]
}
"""

    theirs = """
{
  "hooks": ["pre_tool_use", "post_tool_use", "new_framework_hook"]
}
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "success"
    merged = json.loads(result.merged_content)

    assert "custom_hook" in merged["hooks"]
    assert "new_framework_hook" in merged["hooks"]
```

**Expected**: ✅ Auto-merge - union of arrays

---

### Test 3.4: Value Conflict

**Scenario**: Both user and framework set same key to different values

```python
@pytest.mark.asyncio
async def test_json_value_conflict():
    """Both modified same value."""
    base = """
{
  "timeout": 30,
  "version": "1.0"
}
"""

    ours = """
{
  "timeout": 60,
  "version": "1.0"
}
"""

    theirs = """
{
  "timeout": 45,
  "version": "1.1"
}
"""

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "conflict"
    assert len(result.conflicts) >= 1  # At least timeout conflict
```

**Expected**: ⚠️ Conflict - value mismatch

---

## 4. Integration Tests

### Test 4.1: Complete Hook Update Workflow

**Scenario**: Full workflow of updating hook with merge

```python
@pytest.mark.asyncio
async def test_hook_update_workflow():
    """Complete update workflow with merge."""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    hooks_dir = project_path / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)

    hook_path = hooks_dir / "pre_tool_use.py"

    # Initial hook (base version)
    base_content = """
def pre_tool_use(tool_name, args):
    return {"decision": "allow"}
"""

    # User modified hook
    user_content = """
import logging

def pre_tool_use(tool_name, args):
    logging.info(f"Tool: {tool_name}")
    return {"decision": "allow"}
"""

    # Framework update
    new_content = """
from typing import Dict

def pre_tool_use(tool_name: str, args: Dict) -> Dict:
    return {"decision": "allow"}
"""

    hook_path.write_text(user_content)

    manager = HookUpdateManager(str(project_path))
    result = await manager.update_hook("pre_tool_use.py", new_content, base_version="v1.0")

    assert result.status == "success"
    assert "import logging" in hook_path.read_text()
    assert "from typing import Dict" in hook_path.read_text()
```

**Expected**: ✅ Hook updated with merged content

---

### Test 4.2: Conflict Handling Workflow

**Scenario**: Merge conflict triggers notification

```python
@pytest.mark.asyncio
async def test_conflict_notification():
    """Conflict triggers user notification."""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    hooks_dir = project_path / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)

    hook_path = hooks_dir / "pre_tool_use.py"

    base = "def hook(): return allow()"
    ours = "def hook():\n    if check(): return allow()"
    theirs = "def hook():\n    if different(): return allow()"

    hook_path.write_text(ours)

    manager = HookUpdateManager(str(project_path))
    result = await manager.update_hook("pre_tool_use.py", theirs, "v1.0")

    assert result.status == "conflict"

    # Conflict file created
    conflict_path = hook_path.with_suffix(".py.CONFLICT")
    assert conflict_path.exists()
```

**Expected**: ✅ Conflict file created, user notified

---

## 5. Edge Case Tests

### Test 5.1: Empty File Merge

**Scenario**: One or more files are empty

```python
@pytest.mark.asyncio
async def test_empty_file_merge():
    """Handle merging with empty files."""
    base = ""
    ours = "def hook():\n    pass"
    theirs = ""

    result = await three_way_merge(base, ours, theirs)

    # Should preserve user content
    assert "def hook" in result.merged_content
```

**Expected**: ✅ Preserve non-empty version

---

### Test 5.2: Identical Versions

**Scenario**: All three versions are identical

```python
@pytest.mark.asyncio
async def test_identical_versions():
    """All versions are the same."""
    content = "def hook():\n    pass"

    result = await three_way_merge(content, content, content)

    assert result.status == "success"
    assert result.merged_content == content
    assert len(result.conflicts) == 0
```

**Expected**: ✅ No changes needed

---

### Test 5.3: Syntax Error Handling

**Scenario**: One version has syntax errors

```python
@pytest.mark.asyncio
async def test_syntax_error():
    """File contains syntax errors."""
    base = "def hook():\n    pass"
    ours = "def hook():\n    pass"
    theirs = "def hook(\n    SYNTAX ERROR HERE"  # Invalid

    result = await three_way_merge(base, ours, theirs)

    assert result.status in ["error", "conflict"]
    # Should fall back to keeping OURS
    assert result.merged_content is not None
```

**Expected**: ⚠️ Handle gracefully - keep current version

---

### Test 5.4: Large File Performance

**Scenario**: Merge performance with large files (>10MB)

```python
@pytest.mark.asyncio
async def test_large_file_performance():
    """Merge should be fast even for large files."""
    # Generate large content
    base = "# BASE\n" + "\n".join([f"section_{i}" for i in range(1000)])
    ours = base + "\n# USER SECTION"
    theirs = base + "\n# FRAMEWORK SECTION"

    import time
    start = time.time()
    result = await three_way_merge(base, ours, theirs)
    elapsed = time.time() - start

    assert elapsed < 1.0  # Should complete in under 1 second
    assert result.status == "success"
```

**Expected**: ✅ Complete in <1 second

---

## 6. Regression Tests

### Test 6.1: Git Merge Compatibility

**Scenario**: Results match git merge behavior

```python
@pytest.mark.asyncio
async def test_git_merge_compat():
    """Verify results match git's 3-way merge."""
    # Use actual git to merge, compare with our implementation

    base = "line1\nline2\nline3"
    ours = "line1\nline2_user\nline3"
    theirs = "line1\nline2\nline3_framework"

    # Git merge result
    git_result = run_git_merge(base, ours, theirs)

    # Our merge
    our_result = await three_way_merge(base, ours, theirs)

    # Should be similar (allowing for formatting differences)
    assert git_result.status == our_result.status
```

**Expected**: ✅ Compatible with git behavior

---

## 7. Test Fixtures

```python
# tests/merge/conftest.py

import pytest
from pathlib import Path

@pytest.fixture
def test_project(tmp_path):
    """Create test project structure."""
    project = tmp_path / "test_project"
    project.mkdir()

    (project / ".claude").mkdir()
    (project / ".claude" / "hooks").mkdir()
    (project / ".stravinsky").mkdir()

    return project

@pytest.fixture
def sample_hook():
    """Sample Python hook for testing."""
    return """
def pre_tool_use(tool_name, args):
    '''Handle pre-tool execution.'''
    return {"decision": "allow"}
"""

@pytest.fixture
def sample_skill():
    """Sample Markdown skill for testing."""
    return """---
description: Test skill
version: 1.0
---

# Test Skill

This is a test skill.
"""

@pytest.fixture
def sample_config():
    """Sample JSON config for testing."""
    return """
{
  "hooks": ["pre_tool_use"],
  "version": "1.0"
}
"""
```

---

## 8. Running Tests

```bash
# Run all merge tests
pytest tests/merge/ -v

# Run specific test file
pytest tests/merge/test_python_merge.py -v

# Run with coverage
pytest tests/merge/ --cov=mcp_bridge.merge

# Run slow tests only
pytest tests/merge/ -m slow

# Run specific test
pytest tests/merge/test_python_merge.py::test_python_no_user_change -v
```

---

## 9. Test Coverage Goals

- **Python handlers**: 95%+ coverage
- **Markdown handlers**: 90%+ coverage
- **JSON handlers**: 95%+ coverage
- **Conflict detection**: 90%+ coverage
- **Integration**: 85%+ coverage

---

## 10. Performance Benchmarks

| Operation | Target | Acceptable |
|-----------|--------|-----------|
| Small file (<1KB) merge | <50ms | <100ms |
| Medium file (10-100KB) merge | <200ms | <500ms |
| Large file (1-10MB) merge | <1s | <2s |
| Conflict detection | <50ms | <100ms |
| Conflict marker generation | <100ms | <200ms |

---

## Continuous Integration

All tests run on:
- Python 3.11, 3.12, 3.13
- Linux, macOS
- Pull request before merge
- Deployment verification
