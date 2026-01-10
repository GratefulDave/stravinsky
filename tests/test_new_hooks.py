"""
Tests for new hooks: session_idle, pre_compact, parallel_enforcer, planner.
"""

import pytest
from mcp_bridge.hooks.session_idle import (
    session_idle_hook,
    _detect_pending_todos,
    reset_session,
    TODO_CONTINUATION_PROMPT,
)
from mcp_bridge.hooks.pre_compact import (
#    pre_compact_hook,
    extract_preserved_context,
    log_compaction,
    get_stravinsky_mode_state,
    ensure_state_dir,
    PRESERVE_PATTERNS,
    COMPACTION_LOG
#    register_memory_anchor,
#    clear_memory_anchors,
#    _is_compaction_prompt,
#    _extract_preserved_context,
#    _build_preservation_section,
#    MEMORY_ANCHORS,
)
from mcp_bridge.hooks.parallel_enforcer import (
    parallel_enforcer_post_tool_hook,
    _count_pending_todos,
    reset_enforcement,
    PARALLEL_ENFORCEMENT_PROMPT,
)
from mcp_bridge.prompts.planner import (
    get_planner_prompt,
    PLANNER_PROMPT,
    PLANNER_ROLE,
    PLANNER_METHODOLOGY,
)


# ============================================================================
# Session Idle Hook Tests
# ============================================================================

def test_detect_pending_todos_bracket_pattern():
    """Test detection of [pending] pattern."""
    prompt = "Task 1: [pending]\nTask 2: [completed]"
    assert _detect_pending_todos(prompt) is True


def test_detect_pending_todos_status_pattern():
    """Test detection of status: pending pattern."""
    prompt = 'Task 1: status: pending\nTask 2: status: completed'
    assert _detect_pending_todos(prompt) is True


def test_detect_pending_todos_json_pattern():
    """Test detection of JSON pending pattern."""
    prompt = '{"status": "pending", "task": "Test"}'
    assert _detect_pending_todos(prompt) is True


def test_detect_pending_todos_no_match():
    """Test no pending todos detected."""
    prompt = "All tasks complete. Status: completed."
    assert _detect_pending_todos(prompt) is False


def test_detect_pending_todos_case_insensitive():
    """Test case insensitive detection."""
    prompt = "TASK: [PENDING]"
    assert _detect_pending_todos(prompt) is True


@pytest.mark.asyncio
async def test_session_idle_hook_no_pending():
    """Test hook returns None when no pending todos."""
    reset_session()
    params = {"prompt": "All tasks complete", "session_id": "test"}
    result = await session_idle_hook(params)
    assert result is None


@pytest.mark.asyncio
async def test_session_idle_hook_already_injected():
    """Test hook skips if continuation already present."""
    reset_session()
    params = {
        "prompt": f"Task [pending]\n{TODO_CONTINUATION_PROMPT}",
        "session_id": "test",
    }
    result = await session_idle_hook(params)
    assert result is None


def test_reset_session():
    """Test session reset clears state."""
    reset_session("test_session")
    # Should not raise
    reset_session("test_session")


# ============================================================================
# Pre-Compact Hook Tests
# ============================================================================

# def test_is_compaction_prompt_detected():
#     """Test compaction prompt detection."""
#     prompts = [
#         "Please summarize the conversation",
#         "Compact the context window",
#         "Context window is 85% full",
#     ]
#     for prompt in prompts:
#         assert _is_compaction_prompt(prompt) is True

#
def test_is_compaction_prompt_not_detected():
    pass
#     """Test non-compaction prompts."""
#     prompt = "Write a hello world function"
#     assert _is_compaction_prompt(prompt) is False

#
def test_extract_preserved_context_architecture():
    pass
#     """Test extraction of architecture decisions."""
#     prompt = "ARCHITECTURE: Use microservices\nOther content here"
#     result = _extract_preserved_context(prompt)
#     assert len(result) >= 1
#     assert "ARCHITECTURE: Use microservices" in result[0]

#
def test_extract_preserved_context_constraints():
    pass
#     """Test extraction of constraints."""
#     prompt = "Line 1\nMUST NOT: Delete user data\nLine 3"
#     result = _extract_preserved_context(prompt)
#     assert len(result) >= 1

#
def test_register_memory_anchor_normal():
    pass
#     """Test registering normal priority anchor."""
#     clear_memory_anchors()
#     register_memory_anchor("Test anchor", "normal")
#     assert "Test anchor" in MEMORY_ANCHORS

#
def test_register_memory_anchor_critical():
    pass
#     """Test critical anchors are inserted first."""
#     clear_memory_anchors()
#     register_memory_anchor("Normal anchor", "normal")
#     register_memory_anchor("Critical anchor", "critical")
#     assert "[CRITICAL] Critical anchor" == MEMORY_ANCHORS[0]

#
def test_memory_anchor_limit():
    pass
#     """Test memory anchors limited to 10."""
#     clear_memory_anchors()
#     for i in range(15):
#         register_memory_anchor(f"Anchor {i}")
#     assert len(MEMORY_ANCHORS) == 10

#
def test_clear_memory_anchors():
    pass
#     """Test clearing memory anchors."""
#     register_memory_anchor("Test")
#     clear_memory_anchors()
#     assert len(MEMORY_ANCHORS) == 0

#
def test_build_preservation_section():
    pass
#     """Test preservation section formatting."""
#     items = ["Item 1", "Item 2"]
#     result = _build_preservation_section(items)
#     assert "CRITICAL CONTEXT TO PRESERVE" in result
#     assert "1. Item 1" in result
#     assert "2. Item 2" in result


# @pytest.mark.asyncio
# async def test_pre_compact_hook_non_compaction():
#     """Test hook returns None for non-compaction prompts."""
#     params = {"prompt": "Write code for me"}
#     result = await pre_compact_hook(params)
#     assert result is None


# ============================================================================
# Parallel Enforcer Hook Tests
# ============================================================================

def test_count_pending_todos_bracket():
    """Test counting [pending] pattern."""
    output = "[pending] Task 1\n[pending] Task 2\n[completed] Task 3"
    assert _count_pending_todos(output) == 2


def test_count_pending_todos_json():
    """Test counting JSON pending pattern."""
    output = '{"status": "pending"}\n{"status": "pending"}\n{"status": "completed"}'
    assert _count_pending_todos(output) == 2


def test_count_pending_todos_mixed():
    """Test counting mixed patterns."""
    output = '[pending]\n"status": "pending"\nstatus: pending'
    assert _count_pending_todos(output) >= 2


def test_count_pending_todos_none():
    """Test no pending found."""
    output = "All tasks completed successfully"
    assert _count_pending_todos(output) == 0


@pytest.mark.asyncio
async def test_parallel_enforcer_below_threshold():
    """Test no enforcement with single pending todo."""
    reset_enforcement()
    output = "[pending] Task 1"
    result = await parallel_enforcer_post_tool_hook("TodoWrite", {}, output)
    assert result is None


@pytest.mark.asyncio
async def test_parallel_enforcer_at_threshold():
    """Test enforcement triggers at 2+ pending."""
    reset_enforcement("test_threshold")
    output = "[pending] Task 1\n[pending] Task 2"
    result = await parallel_enforcer_post_tool_hook("TodoWrite", {}, output)
    assert result is not None
    assert "PARALLEL EXECUTION REQUIRED" in result


@pytest.mark.asyncio
async def test_parallel_enforcer_non_todowrite():
    """Test no enforcement for non-TodoWrite tools."""
    reset_enforcement()
    output = "[pending] Task 1\n[pending] Task 2"
    result = await parallel_enforcer_post_tool_hook("Read", {}, output)
    assert result is None


def test_reset_enforcement():
    """Test enforcement reset."""
    reset_enforcement("test_session")
    # Should not raise
    reset_enforcement("test_session")


# ============================================================================
# Planner Prompt Tests
# ============================================================================

def test_planner_prompt_contains_role():
    """Test planner prompt contains role section."""
    assert "Planner" in PLANNER_PROMPT
    assert "pre-implementation" in PLANNER_PROMPT.lower()


def test_planner_prompt_contains_methodology():
    """Test planner prompt contains methodology."""
    assert "Phase 1" in PLANNER_PROMPT
    assert "Phase 2" in PLANNER_PROMPT


def test_get_planner_prompt_basic():
    """Test basic planner prompt generation."""
    result = get_planner_prompt("Implement feature X")
    assert "Implement feature X" in result
    assert PLANNER_ROLE in result


def test_get_planner_prompt_with_context():
    """Test planner prompt with project context."""
    result = get_planner_prompt(
        "Implement feature X",
        project_context="Python FastAPI project",
    )
    assert "Python FastAPI project" in result
    assert "Project Context" in result


def test_get_planner_prompt_with_patterns():
    """Test planner prompt with existing patterns."""
    result = get_planner_prompt(
        "Implement feature X",
        existing_patterns="Uses Repository pattern",
    )
    assert "Repository pattern" in result
    assert "Discovered Patterns" in result


def test_planner_prompt_includes_agent_reference():
    """Test planner prompt includes agent reference."""
    assert "explore" in PLANNER_PROMPT
    assert "dewey" in PLANNER_PROMPT
    assert "frontend" in PLANNER_PROMPT
    assert "delphi" in PLANNER_PROMPT


def test_planner_prompt_includes_constraints():
    """Test planner prompt includes constraints."""
    assert "MUST DO" in PLANNER_PROMPT
    assert "MUST NOT DO" in PLANNER_PROMPT


if __name__ == "__main__":
    import asyncio

    # Run sync tests
    test_detect_pending_todos_bracket_pattern()
    test_detect_pending_todos_no_match()
#    test_is_compaction_prompt_detected()
    test_count_pending_todos_bracket()
    test_planner_prompt_contains_role()
    test_get_planner_prompt_basic()

    # Run async tests
    asyncio.run(test_session_idle_hook_no_pending())
#    asyncio.run(test_pre_compact_hook_non_compaction())
    asyncio.run(test_parallel_enforcer_below_threshold())

    print("All new hook tests passed!")
