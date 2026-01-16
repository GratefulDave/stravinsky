# Test Status - Stravinsky Improvements

## Existing Tests (Already Implemented)

### Phase 1: Semantic Search Auto-Index
- ✅ **File**: `tests/test_auto_indexing.py`
- **Created**: Jan 13, 2026
- **Coverage**: Auto-index detection, user prompts, timeout handling

### Phase 2: TODO Verification
- ✅ **File**: `tests/test_todo_verification.py`
- **Status**: Exists (need to verify coverage)
- **Expected Coverage**: Evidence extraction, verification protocol, rejection logic

### Phase 3: Clean Output Formatting
- ✅ **File**: `tests/test_clean_output.py`
- **Created**: Jan 16, 2026
- **Coverage**: OutputMode enum, format_spawn_output(), progress monitoring

### Phase 4: Delegation Enforcement
- ✅ **File**: `tests/test_delegation_enforcement.py`
- **Created**: Jan 16, 2026
- **Coverage**: Mandatory parameters, agent hierarchy validation, tool validation

### Phase 5: Quality Agents
- ❌ **Status**: Tests NOT created yet
- **Need**: `tests/test_momus.py` and `tests/test_comment_checker.py`

## Tests to Create

### 1. test_momus.py

```python
"""Integration tests for Momus quality gate agent."""
import pytest
from mcp_bridge.tools.agent_manager import agent_spawn, agent_output

@pytest.mark.asyncio
async def test_momus_validates_code_quality():
    """Test that Momus validates code quality with lsp_diagnostics."""
    result = await agent_spawn(
        agent_type="momus",
        prompt="Validate code quality in mcp_bridge/tools/semantic_search.py",
        delegation_reason="momus validates code before approval",
        expected_outcome="Quality report with lsp_diagnostics results",
        required_tools=["Read", "lsp_diagnostics"],
    )

    output = await agent_output(result, block=True)

    # Verify momus checked for errors
    assert "lsp_diagnostics" in output or "validation" in output.lower()

@pytest.mark.asyncio
async def test_momus_requires_evidence():
    """Test that Momus requires evidence for approval."""
    result = await agent_spawn(
        agent_type="momus",
        prompt="Validate implementation of Phase 3 clean output",
        delegation_reason="momus quality gate",
        expected_outcome="Approval or rejection with evidence",
        required_tools=["Read", "Grep"],
    )

    output = await agent_output(result, block=True)

    # Verify momus provides evidence (file paths, tool outputs)
    assert any(
        marker in output
        for marker in ["src/", "mcp_bridge/", "lsp_diagnostics", "tests/"]
    )
```

### 2. test_comment_checker.py

```python
"""Integration tests for Comment-Checker documentation validator."""
import pytest
from mcp_bridge.tools.agent_manager import agent_spawn, agent_output

@pytest.mark.asyncio
async def test_comment_checker_finds_undocumented_code():
    """Test that comment_checker finds functions without docstrings."""
    result = await agent_spawn(
        agent_type="comment_checker",
        prompt="Find undocumented public functions in mcp_bridge/tools/",
        delegation_reason="comment_checker validates documentation",
        expected_outcome="List of undocumented functions with file:line",
        required_tools=["Read", "ast_grep_search"],
    )

    output = await agent_output(result, block=True)

    # Verify comment_checker used ast-grep or similar
    assert any(
        marker in output
        for marker in ["def ", "function", "docstring", "comment"]
    )

@pytest.mark.asyncio
async def test_comment_checker_validates_todos():
    """Test that comment_checker validates TODO format."""
    result = await agent_spawn(
        agent_type="comment_checker",
        prompt="Find TODOs without issue references in mcp_bridge/",
        delegation_reason="comment_checker validates TODO hygiene",
        expected_outcome="List of orphaned TODOs",
        required_tools=["Grep", "Read"],
    )

    output = await agent_output(result, block=True)

    # Verify comment_checker searched for TODOs
    assert "TODO" in output or "FIXME" in output
```

## Test Running Instructions

### Run All Tests

```bash
# From stravinsky root directory
cd /Users/davidandrews/PycharmProjects/stravinsky

# Run all tests
pytest tests/ -v

# Run specific phase tests
pytest tests/test_delegation_enforcement.py -v
pytest tests/test_clean_output.py -v
pytest tests/test_todo_verification.py -v
pytest tests/test_auto_indexing.py -v
```

### Expected Results

All tests should pass with the following validations:

1. **Phase 1**: Auto-index prompt appears when index missing
2. **Phase 2**: Verification rejects claims without evidence
3. **Phase 3**: Clean output format is under 100 chars
4. **Phase 4**: Delegation fails when required params missing
5. **Phase 5**: Quality agents exist and can be spawned

## Manual Verification Checklist

### Phase 1: Semantic Search Auto-Index
- [ ] Run `semantic_search()` on project with no index
- [ ] Verify Y/N prompt appears (30s timeout)
- [ ] Answer Y → index creates → watcher starts
- [ ] Answer N → error message returned

### Phase 2: TODO Verification
- [ ] Mark a TODO complete without evidence
- [ ] Verify system reminds about evidence requirement
- [ ] Mark complete with file:line evidence
- [ ] Verify system accepts it

### Phase 3: Clean Output
- [ ] Spawn an agent with default CLEAN mode
- [ ] Verify output: `✓ agent:model → task_id`
- [ ] Wait 10s → verify progress message appears
- [ ] Wait for completion → verify completion message

### Phase 4: Delegation Enforcement
- [ ] Try to spawn agent without delegation_reason
- [ ] Verify error with clear message
- [ ] Spawn with all required params
- [ ] Verify success

### Phase 5: Quality Agents
- [ ] Spawn momus agent to validate code
- [ ] Verify momus runs lsp_diagnostics
- [ ] Spawn comment_checker to find undocumented code
- [ ] Verify comment_checker uses ast-grep

### Model Routing Fix
- [ ] Spawn implementation-lead agent
- [ ] Verify it uses sonnet (not haiku)
- [ ] Check agent output format shows correct model

## CI/CD Integration

Add to deployment pipeline:

```bash
# .github/workflows/test.yml
steps:
  - name: Run Tests
    run: pytest tests/ -v --tb=short

  - name: Check Coverage
    run: pytest --cov=mcp_bridge tests/
```

## Known Issues

1. **pytest not in system Python**: Need to use venv or uv for testing
2. **Quality agent tests missing**: Need to create test_momus.py and test_comment_checker.py
3. **Manual verification needed**: Some features require human verification (prompts, colors, etc.)

## Next Steps

1. Create test_momus.py and test_comment_checker.py
2. Run full test suite with `pytest tests/ -v`
3. Fix any failing tests
4. Run manual verification checklist
5. Deploy to PyPI if all tests pass
