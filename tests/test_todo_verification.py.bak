"""Test suite for Phase 2: Reinforced TODO Enforcement.

Tests cover:
- Evidence extraction (file paths, URLs, commands)
- Verification protocol (cannot skip todos without evidence)
- Vague claim detection
- File existence verification
- URL accessibility checks
- Command execution proof
"""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_project():
    """Create temporary project with sample files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        (project_path / "src").mkdir()
        (project_path / "src" / "auth.ts").write_text("export function login() {}")
        (project_path / "tests").mkdir()
        (project_path / "tests" / "auth.test.ts").write_text("test('login', () => {})")
        yield str(project_path)


@pytest.fixture
def sample_agent_output():
    """Sample agent output with various evidence types."""
    return """
    I've completed the tasks:

    1. Created authentication module in src/auth.ts
    2. Added tests in tests/auth.test.ts
    3. Followed the official docs at https://example.com/auth-guide
    4. Ran `npm test` to verify all tests pass
    """


# ============================================================================
# TEST: Evidence Extraction
# ============================================================================


@pytest.mark.asyncio
async def test_extract_file_paths(sample_agent_output):
    """Test extraction of file paths from agent output."""
    from mcp_bridge.tools.todo_enforcer import _extract_evidence

    evidence = _extract_evidence(sample_agent_output)

    # Should find file paths
    assert "src/auth.ts" in evidence["files"]
    assert "tests/auth.test.ts" in evidence["files"]


@pytest.mark.asyncio
async def test_extract_urls(sample_agent_output):
    """Test extraction of URLs from agent output."""
    from mcp_bridge.tools.todo_enforcer import _extract_evidence

    evidence = _extract_evidence(sample_agent_output)

    # Should find URLs
    assert "https://example.com/auth-guide" in evidence["urls"]


@pytest.mark.asyncio
async def test_extract_commands(sample_agent_output):
    """Test extraction of shell commands from agent output."""
    from mcp_bridge.tools.todo_enforcer import _extract_evidence

    evidence = _extract_evidence(sample_agent_output)

    # Should find commands
    assert "npm test" in evidence["commands"]


@pytest.mark.asyncio
async def test_extract_evidence_no_matches():
    """Test evidence extraction with no matches."""
    from mcp_bridge.tools.todo_enforcer import _extract_evidence

    output = "I thought about the problem but didn't do anything concrete."

    evidence = _extract_evidence(output)

    assert len(evidence["files"]) == 0
    assert len(evidence["urls"]) == 0
    assert len(evidence["commands"]) == 0


@pytest.mark.asyncio
async def test_extract_evidence_mixed_formats():
    """Test evidence extraction with various formatting styles."""
    from mcp_bridge.tools.todo_enforcer import _extract_evidence

    output = """
    Files modified:
    - `src/app.py`
    - Created ./lib/utils.js

    References:
    * https://docs.python.org/3/
    * See: http://github.com/repo/file

    Commands executed:
    $ pytest tests/
    > npm run build
    """

    evidence = _extract_evidence(output)

    assert "src/app.py" in evidence["files"]
    assert "lib/utils.js" in evidence["files"]
    assert "https://docs.python.org/3/" in evidence["urls"]
    assert "http://github.com/repo/file" in evidence["urls"]
    assert "pytest tests/" in evidence["commands"]
    assert "npm run build" in evidence["commands"]


# ============================================================================
# TEST: Verification Protocol
# ============================================================================


@pytest.mark.asyncio
async def test_cannot_skip_todo_without_evidence(temp_project):
    """Test agent cannot mark todo complete without evidence."""
    from mcp_bridge.tools.todo_enforcer import verify_todo_completion

    todo = "Create src/auth.ts"
    output = "I completed the task."  # Vague claim, no evidence

    result = await verify_todo_completion(
        todo=todo,
        agent_output=output,
        project_path=temp_project,
    )

    # Should fail verification
    assert result["verified"] is False
    assert "no evidence" in result["reason"].lower() or "vague" in result["reason"].lower()


@pytest.mark.asyncio
async def test_todo_verified_with_file_evidence(temp_project):
    """Test todo passes verification when file exists."""
    from mcp_bridge.tools.todo_enforcer import verify_todo_completion

    todo = "Create src/auth.ts"
    output = "Created authentication module in src/auth.ts"

    result = await verify_todo_completion(
        todo=todo,
        agent_output=output,
        project_path=temp_project,
    )

    # Should pass (file exists)
    assert result["verified"] is True


@pytest.mark.asyncio
async def test_todo_fails_when_file_missing(temp_project):
    """Test todo fails verification when mentioned file doesn't exist."""
    from mcp_bridge.tools.todo_enforcer import verify_todo_completion

    todo = "Create src/database.ts"
    output = "Created database module in src/database.ts"

    result = await verify_todo_completion(
        todo=todo,
        agent_output=output,
        project_path=temp_project,
    )

    # Should fail (file doesn't exist)
    assert result["verified"] is False
    assert "does not exist" in result["reason"].lower()


# ============================================================================
# TEST: Vague Claim Detection
# ============================================================================


@pytest.mark.asyncio
async def test_detect_vague_claim_completed():
    """Test detection of vague 'I completed it' claims."""
    from mcp_bridge.tools.todo_enforcer import _is_vague_claim

    vague_outputs = [
        "I completed the task.",
        "Done.",
        "Task finished.",
        "I did it.",
        "Completed successfully.",
    ]

    for output in vague_outputs:
        assert _is_vague_claim(output) is True, f"Should detect vague: {output}"


@pytest.mark.asyncio
async def test_detect_specific_claims_not_vague():
    """Test specific claims are not marked as vague."""
    from mcp_bridge.tools.todo_enforcer import _is_vague_claim

    specific_outputs = [
        "Created src/auth.ts with login function",
        "Modified package.json to add jest dependency",
        "Ran npm test - all 42 tests pass",
        "See implementation in commit abc123",
    ]

    for output in specific_outputs:
        assert _is_vague_claim(output) is False, f"Should NOT be vague: {output}"


@pytest.mark.asyncio
async def test_vague_claim_requires_evidence(temp_project):
    """Test vague claims fail even if file exists."""
    from mcp_bridge.tools.todo_enforcer import verify_todo_completion

    todo = "Create src/auth.ts"
    output = "Done."  # Vague, even though file exists

    result = await verify_todo_completion(
        todo=todo,
        agent_output=output,
        project_path=temp_project,
    )

    # Should fail due to vague claim
    assert result["verified"] is False
    assert "vague" in result["reason"].lower()


# ============================================================================
# TEST: File Existence Verification
# ============================================================================


@pytest.mark.asyncio
async def test_verify_file_exists(temp_project):
    """Test file existence check passes when file exists."""
    from mcp_bridge.tools.todo_enforcer import _verify_file_exists

    result = _verify_file_exists("src/auth.ts", project_path=temp_project)

    assert result is True


@pytest.mark.asyncio
async def test_verify_file_missing(temp_project):
    """Test file existence check fails when file missing."""
    from mcp_bridge.tools.todo_enforcer import _verify_file_exists

    result = _verify_file_exists("src/missing.ts", project_path=temp_project)

    assert result is False


@pytest.mark.asyncio
async def test_verify_file_with_glob_pattern(temp_project):
    """Test file verification supports glob patterns."""
    from mcp_bridge.tools.todo_enforcer import _verify_file_exists

    # Should find tests/auth.test.ts
    result = _verify_file_exists("tests/*.test.ts", project_path=temp_project)

    assert result is True


@pytest.mark.asyncio
async def test_verify_absolute_path(temp_project):
    """Test file verification works with absolute paths."""
    from mcp_bridge.tools.todo_enforcer import _verify_file_exists

    abs_path = str(Path(temp_project) / "src" / "auth.ts")

    result = _verify_file_exists(abs_path, project_path=temp_project)

    assert result is True


# ============================================================================
# TEST: URL Accessibility Checks
# ============================================================================


@pytest.mark.asyncio
async def test_verify_url_accessible():
    """Test URL verification passes for accessible URLs."""
    from mcp_bridge.tools.todo_enforcer import _verify_url_accessible

    with patch("requests.head") as mock_head:
        mock_head.return_value.status_code = 200

        result = await _verify_url_accessible("https://example.com/docs")

        assert result is True


@pytest.mark.asyncio
async def test_verify_url_not_found():
    """Test URL verification fails for 404s."""
    from mcp_bridge.tools.todo_enforcer import _verify_url_accessible

    with patch("requests.head") as mock_head:
        mock_head.return_value.status_code = 404

        result = await _verify_url_accessible("https://example.com/missing")

        assert result is False


@pytest.mark.asyncio
async def test_verify_url_timeout():
    """Test URL verification handles timeouts gracefully."""
    from mcp_bridge.tools.todo_enforcer import _verify_url_accessible
    import requests

    with patch("requests.head", side_effect=requests.Timeout()):
        result = await _verify_url_accessible("https://example.com/slow")

        # Timeout counts as failure
        assert result is False


@pytest.mark.asyncio
async def test_verify_url_redirects_followed():
    """Test URL verification follows redirects."""
    from mcp_bridge.tools.todo_enforcer import _verify_url_accessible

    with patch("requests.head") as mock_head:
        # First call: redirect, second call: success
        mock_head.side_effect = [
            MagicMock(status_code=301, headers={"Location": "https://new.com"}),
            MagicMock(status_code=200),
        ]

        result = await _verify_url_accessible("https://old.com/docs")

        assert result is True


# ============================================================================
# TEST: Command Execution Proof
# ============================================================================


@pytest.mark.asyncio
async def test_command_evidence_in_output():
    """Test command mentioned in output counts as evidence."""
    from mcp_bridge.tools.todo_enforcer import _extract_evidence

    output = "Ran `npm test` and all 42 tests passed"

    evidence = _extract_evidence(output)

    assert "npm test" in evidence["commands"]


@pytest.mark.asyncio
async def test_command_with_output_strengthens_evidence():
    """Test command with output is stronger evidence."""
    from mcp_bridge.tools.todo_enforcer import _score_evidence_strength

    weak_output = "I ran the tests"
    strong_output = """
    Ran `npm test`:

    PASS tests/auth.test.ts
      ✓ login works (5ms)
      ✓ logout works (3ms)

    Tests: 2 passed, 2 total
    """

    weak_score = _score_evidence_strength(weak_output)
    strong_score = _score_evidence_strength(strong_output)

    assert strong_score > weak_score


# ============================================================================
# TEST: Multi-Evidence Verification
# ============================================================================


@pytest.mark.asyncio
async def test_multiple_evidence_types_strengthen_verification(temp_project):
    """Test multiple evidence types increase confidence."""
    from mcp_bridge.tools.todo_enforcer import verify_todo_completion

    todo = "Implement authentication"
    output = """
    Implemented authentication system:

    1. Created src/auth.ts with login/logout functions
    2. Added tests in tests/auth.test.ts
    3. Followed best practices from https://auth0.com/docs
    4. Ran `npm test` - all tests pass
    """

    result = await verify_todo_completion(
        todo=todo,
        agent_output=output,
        project_path=temp_project,
    )

    # Should pass with high confidence (multiple evidence types)
    assert result["verified"] is True
    assert result["confidence"] == "high"


@pytest.mark.asyncio
async def test_single_evidence_medium_confidence(temp_project):
    """Test single evidence type gives medium confidence."""
    from mcp_bridge.tools.todo_enforcer import verify_todo_completion

    todo = "Create auth module"
    output = "Created src/auth.ts"

    result = await verify_todo_completion(
        todo=todo,
        agent_output=output,
        project_path=temp_project,
    )

    assert result["verified"] is True
    assert result["confidence"] == "medium"


# ============================================================================
# TEST: Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_empty_output_fails_verification():
    """Test empty agent output fails verification."""
    from mcp_bridge.tools.todo_enforcer import verify_todo_completion

    result = await verify_todo_completion(
        todo="Create auth module",
        agent_output="",
        project_path="/tmp",
    )

    assert result["verified"] is False


@pytest.mark.asyncio
async def test_todo_with_multiple_files(temp_project):
    """Test todo requiring multiple files."""
    from mcp_bridge.tools.todo_enforcer import verify_todo_completion

    todo = "Implement auth with tests"
    output = "Created src/auth.ts and tests/auth.test.ts"

    result = await verify_todo_completion(
        todo=todo,
        agent_output=output,
        project_path=temp_project,
    )

    # Both files exist
    assert result["verified"] is True


@pytest.mark.asyncio
async def test_partial_completion_fails(temp_project):
    """Test partial completion (some files missing) fails."""
    from mcp_bridge.tools.todo_enforcer import verify_todo_completion

    todo = "Implement auth with tests and docs"
    output = "Created src/auth.ts, tests/auth.test.ts, and docs/auth.md"

    result = await verify_todo_completion(
        todo=todo,
        agent_output=output,
        project_path=temp_project,
    )

    # docs/auth.md doesn't exist
    assert result["verified"] is False
    assert "docs/auth.md" in result["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
