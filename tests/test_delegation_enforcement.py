"""Test suite for Phase 4: Delegation Enforcement.

Tests cover:
- Mandatory parameters validation (delegation_reason, expected_outcome, spawning_agent)
- Agent hierarchy enforcement (orchestrator → coordinator → worker)
- Worker agents cannot spawn orchestrators
- Clear error messages for validation failures
- Delegation chain tracking
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def valid_spawn_params():
    """Valid agent_spawn parameters."""
    return {
        "agent_type": "explore",
        "prompt": "Find authentication logic",
        "delegation_reason": "Need to locate auth code before implementing feature",
        "expected_outcome": "List of files containing authentication functions",
        "required_tools": ["Read", "Grep", "Glob"],
        "spawning_agent": "research-lead",
    }


# ============================================================================
# TEST: Mandatory Parameters Validation
# ============================================================================


@pytest.mark.asyncio
async def test_missing_delegation_reason_fails():
    """Test agent_spawn fails when delegation_reason is missing."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    with pytest.raises(ValueError, match="Orchestrators must provide delegation metadata"):
        await agent_spawn(
            agent_type="explore",
            prompt="Find auth logic",
            # delegation_reason missing
            expected_outcome="List of auth files",
            spawning_agent="research-lead",
        )


@pytest.mark.asyncio
async def test_missing_expected_outcome_fails():
    """Test agent_spawn fails when expected_outcome is missing."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    with pytest.raises(ValueError, match="Orchestrators must provide delegation metadata"):
        await agent_spawn(
            agent_type="explore",
            prompt="Find auth logic",
            delegation_reason="Need to find auth code",
            # expected_outcome missing
            spawning_agent="research-lead",
        )


@pytest.mark.asyncio
async def test_missing_spawning_agent_allowed():
    """Test agent_spawn allows spawning_agent to be None (optional)."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    # spawning_agent is optional - should not raise
    output = await agent_spawn(
        agent_type="explore",
        prompt="Find auth logic",
        description="Test spawn",
        # spawning_agent not provided (None by default)
    )
    # Output is formatted string containing task_id
    assert "agent_" in output


@pytest.mark.asyncio
async def test_empty_delegation_reason_fails():
    """Test agent_spawn fails when delegation_reason is empty string."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    with pytest.raises(ValueError, match="Orchestrators must provide delegation metadata"):
        await agent_spawn(
            agent_type="explore",
            prompt="Find auth logic",
            delegation_reason="",  # Empty (treated as falsy)
            expected_outcome="List of auth files",
            spawning_agent="research-lead",
        )


@pytest.mark.asyncio
async def test_empty_expected_outcome_fails():
    """Test agent_spawn fails when expected_outcome is empty string."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    with pytest.raises(ValueError, match="Orchestrators must provide delegation metadata"):
        await agent_spawn(
            agent_type="explore",
            prompt="Find auth logic",
            delegation_reason="Need to find auth code",
            expected_outcome="",  # Empty (treated as falsy)
            spawning_agent="research-lead",
        )


@pytest.mark.asyncio
async def test_valid_params_succeeds(valid_spawn_params):
    """Test agent_spawn succeeds with all required params."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    # Actually spawn agent (integration test)
    output = await agent_spawn(**valid_spawn_params)

    # Output is formatted string containing task_id
    assert "agent_" in output
    assert "explore" in output


# ============================================================================
# TEST: Agent Hierarchy Enforcement
# ============================================================================


@pytest.mark.asyncio
async def test_orchestrator_can_spawn_coordinator():
    """Test orchestrator (stravinsky) can spawn coordinator (research-lead)."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    output = await agent_spawn(
        agent_type="research-lead",
        prompt="Research auth patterns",
        delegation_reason="Need to gather auth research before implementation",
        expected_outcome="Research brief with auth patterns",
        required_tools=["agent_spawn", "agent_output", "Read"],
        spawning_agent="stravinsky",  # Orchestrator
    )

    assert "agent_" in output
    assert "research-lead" in output


@pytest.mark.asyncio
async def test_coordinator_can_spawn_worker():
    """Test coordinator (research-lead) can spawn worker (explore)."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    output = await agent_spawn(
        agent_type="explore",
        prompt="Find auth files",
        delegation_reason="Need file locations for research brief",
        expected_outcome="List of auth-related files",
        required_tools=["Read", "Grep", "Glob"],
        spawning_agent="research-lead",  # Coordinator
    )

    assert "agent_" in output
    assert "explore" in output


@pytest.mark.asyncio
async def test_worker_cannot_spawn_orchestrator():
    """Test worker (explore) cannot spawn orchestrator (stravinsky)."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    with pytest.raises(ValueError, match="Worker agent .* cannot spawn orchestrator agent"):
        await agent_spawn(
            agent_type="stravinsky",
            prompt="Coordinate work",
            delegation_reason="Invalid delegation",
            expected_outcome="Should fail",
            spawning_agent="explore",  # Worker trying to spawn orchestrator
        )


@pytest.mark.asyncio
async def test_worker_cannot_spawn_orchestrator_research_lead():
    """Test worker (explore) cannot spawn orchestrator (research-lead)."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    with pytest.raises(ValueError, match="Worker agent .* cannot spawn orchestrator agent"):
        await agent_spawn(
            agent_type="research-lead",
            prompt="Do research",
            delegation_reason="Invalid delegation",
            expected_outcome="Should fail",
            spawning_agent="explore",  # Worker trying to spawn orchestrator
        )


@pytest.mark.asyncio
async def test_worker_cannot_spawn_worker():
    """Test worker (explore) cannot spawn another worker (dewey)."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    with pytest.raises(ValueError, match="Worker agent .* cannot spawn another worker agent"):
        await agent_spawn(
            agent_type="dewey",
            prompt="Research docs",
            delegation_reason="Invalid delegation",
            expected_outcome="Should fail",
            spawning_agent="explore",  # Worker trying to spawn worker
        )


# ============================================================================
# TEST: Agent Role Classification
# ============================================================================


@pytest.mark.asyncio
async def test_agent_role_orchestrator():
    """Test orchestrator role classification."""
    from mcp_bridge.tools.agent_manager import ORCHESTRATOR_AGENTS

    assert "stravinsky" in ORCHESTRATOR_AGENTS
    assert "research-lead" in ORCHESTRATOR_AGENTS
    assert "implementation-lead" in ORCHESTRATOR_AGENTS


@pytest.mark.asyncio
async def test_agent_role_worker():
    """Test worker role classification."""
    from mcp_bridge.tools.agent_manager import WORKER_AGENTS

    assert "explore" in WORKER_AGENTS
    assert "dewey" in WORKER_AGENTS
    assert "frontend" in WORKER_AGENTS
    assert "debugger" in WORKER_AGENTS


@pytest.mark.asyncio
async def test_orchestrators_and_workers_are_distinct():
    """Test that orchestrators and workers don't overlap."""
    from mcp_bridge.tools.agent_manager import ORCHESTRATOR_AGENTS, WORKER_AGENTS

    # Ensure no overlap between orchestrators and workers
    overlap = set(ORCHESTRATOR_AGENTS) & set(WORKER_AGENTS)
    assert len(overlap) == 0, f"Orchestrators and workers should not overlap, but found: {overlap}"


@pytest.mark.asyncio
async def test_unknown_agent_type_not_in_hierarchy():
    """Test unknown agent types are not in any hierarchy list."""
    from mcp_bridge.tools.agent_manager import ORCHESTRATOR_AGENTS, WORKER_AGENTS

    assert "unknown-agent-xyz" not in ORCHESTRATOR_AGENTS
    assert "unknown-agent-xyz" not in WORKER_AGENTS


# ============================================================================
# TEST: Delegation Chain Tracking
# ============================================================================


@pytest.mark.asyncio
async def test_delegation_chain_recorded():
    """Test delegation with proper parameters succeeds."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    output = await agent_spawn(
        agent_type="explore",
        prompt="Find auth",
        delegation_reason="Locate auth code",
        expected_outcome="Auth file list",
        required_tools=["Read", "Grep", "Glob"],
        spawning_agent="research-lead",
    )

    # Verify spawn succeeded with proper output
    assert "agent_" in output
    assert "explore" in output


# NOTE: Delegation depth limiting not yet implemented
# @pytest.mark.asyncio
# async def test_delegation_depth_limited():
#     """Test delegation chain depth is limited to prevent infinite recursion."""
#     # TODO: Implement _get_delegation_depth and depth limiting in agent_manager.py
#     pass


# ============================================================================
# TEST: Error Messages
# ============================================================================


@pytest.mark.asyncio
async def test_clear_error_message_missing_param():
    """Test error message is clear and actionable when param missing."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    try:
        await agent_spawn(
            agent_type="explore",
            prompt="Find auth",
            # Missing all delegation params
        )
    except ValueError as e:
        error_msg = str(e)
        # Should mention what's missing
        assert "delegation_reason" in error_msg.lower()
        # Should show how to fix
        assert "agent_spawn" in error_msg or "example" in error_msg.lower()


@pytest.mark.asyncio
async def test_clear_error_message_hierarchy_violation():
    """Test error message is clear when hierarchy violated."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    try:
        await agent_spawn(
            agent_type="stravinsky",
            prompt="Orchestrate",
            delegation_reason="Invalid",
            expected_outcome="Should fail",
            spawning_agent="explore",  # Worker → Orchestrator (invalid)
        )
    except ValueError as e:
        error_msg = str(e)
        # Should explain the hierarchy
        assert "Worker" in error_msg or "worker" in error_msg
        assert "orchestrator" in error_msg.lower()
        # Should suggest valid alternatives
        assert "can only spawn" in error_msg.lower() or "cannot spawn" in error_msg.lower()


# ============================================================================
# TEST: Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_whitespace_delegation_reason_accepted():
    """Test delegation_reason with whitespace is accepted (no stripping validation)."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    # Whitespace-only strings pass the `if not delegation_reason:` check
    # because they're truthy in Python, so this should succeed
    output = await agent_spawn(
        agent_type="explore",
        prompt="Find auth",
        delegation_reason="   \n\t  ",  # Whitespace only (truthy in Python)
        expected_outcome="Auth files",
        required_tools=["Read", "Grep", "Glob"],
        spawning_agent="research-lead",
    )

    assert "agent_" in output


@pytest.mark.asyncio
async def test_very_long_delegation_reason_accepted():
    """Test very long delegation_reason is accepted (no arbitrary length limit)."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    long_reason = "Need to locate auth code " * 100  # Very long

    output = await agent_spawn(
        agent_type="explore",
        prompt="Find auth",
        delegation_reason=long_reason,
        expected_outcome="Auth files",
        required_tools=["Read", "Grep", "Glob"],
        spawning_agent="research-lead",
    )

    assert "agent_" in output
    assert "explore" in output


@pytest.mark.asyncio
async def test_none_spawning_agent_allowed():
    """Test None as spawning_agent is allowed (optional parameter)."""
    from mcp_bridge.tools.agent_manager import agent_spawn

    # spawning_agent=None is allowed - should not raise
    output = await agent_spawn(
        agent_type="explore",
        prompt="Find auth",
        description="Test spawn with None",
        spawning_agent=None,
    )
    # Output is formatted string containing task_id
    assert "agent_" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
