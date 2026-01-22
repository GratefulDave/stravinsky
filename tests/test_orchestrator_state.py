import pytest
from mcp_bridge.orchestrator.enums import OrchestrationPhase
from mcp_bridge.orchestrator.state import OrchestratorState, VALID_TRANSITIONS, PHASE_REQUIREMENTS


def test_phases_enum():
    """Test that all phase enum values are correct."""
    assert OrchestrationPhase.CLASSIFY.value == "classify"
    assert OrchestrationPhase.CONTEXT.value == "context"
    assert OrchestrationPhase.WISDOM.value == "wisdom"
    assert OrchestrationPhase.PLAN.value == "plan"
    assert OrchestrationPhase.VALIDATE.value == "validate"
    assert OrchestrationPhase.DELEGATE.value == "delegate"
    assert OrchestrationPhase.EXECUTE.value == "execute"
    assert OrchestrationPhase.VERIFY.value == "verify"


def test_orchestrator_state_transitions_non_strict():
    """Test basic transitions work with strict_mode=False."""
    state = OrchestratorState(strict_mode=False)
    assert state.current_phase == OrchestrationPhase.CLASSIFY

    # Test valid transition (CLASSIFY → CONTEXT)
    state.transition_to(OrchestrationPhase.CONTEXT)
    assert state.current_phase == OrchestrationPhase.CONTEXT
    assert OrchestrationPhase.CLASSIFY in state.history


def test_orchestrator_state_transitions_with_artifacts():
    """Test transitions work when required artifacts are provided."""
    state = OrchestratorState(strict_mode=True)
    assert state.current_phase == OrchestrationPhase.CLASSIFY

    # Register required artifact for CONTEXT phase
    state.register_artifact("query_classification", "SEMANTIC")

    # Now transition should succeed
    state.transition_to(OrchestrationPhase.CONTEXT)
    assert state.current_phase == OrchestrationPhase.CONTEXT
    assert OrchestrationPhase.CLASSIFY in state.history


def test_required_artifacts():
    """Test that transitions fail without required artifacts in strict mode."""
    state = OrchestratorState(strict_mode=True)

    # Should fail transition to CONTEXT without query_classification
    with pytest.raises(ValueError, match="Missing artifacts"):
        state.transition_to(OrchestrationPhase.CONTEXT)

    # Register required artifact and proceed
    state.register_artifact("query_classification", "PATTERN")
    state.transition_to(OrchestrationPhase.CONTEXT)

    # Register context_summary to proceed to WISDOM
    state.register_artifact("context_summary", "Found 5 files...")
    state.transition_to(OrchestrationPhase.WISDOM)

    # Can proceed to PLAN (no artifacts required)
    state.transition_to(OrchestrationPhase.PLAN)

    # Should fail transition to VALIDATE without plan.md
    with pytest.raises(ValueError, match="Missing artifacts"):
        state.transition_to(OrchestrationPhase.VALIDATE)

    # Register plan.md and proceed
    state.register_artifact("plan.md", "# Plan\n1. Do thing")
    state.transition_to(OrchestrationPhase.VALIDATE)
    assert state.current_phase == OrchestrationPhase.VALIDATE


def test_invalid_transitions():
    """Test that invalid phase transitions are rejected."""
    state = OrchestratorState(strict_mode=False)

    # CLASSIFY can only go to CONTEXT
    with pytest.raises(ValueError, match="Invalid transition"):
        state.transition_to(OrchestrationPhase.PLAN)

    with pytest.raises(ValueError, match="Invalid transition"):
        state.transition_to(OrchestrationPhase.VERIFY)


def test_valid_transitions_map():
    """Test that VALID_TRANSITIONS contains all phases."""
    for phase in OrchestrationPhase:
        assert phase in VALID_TRANSITIONS, f"Missing {phase} in VALID_TRANSITIONS"


def test_phase_requirements_map():
    """Test that PHASE_REQUIREMENTS contains all phases."""
    for phase in OrchestrationPhase:
        assert phase in PHASE_REQUIREMENTS, f"Missing {phase} in PHASE_REQUIREMENTS"


def test_get_phase_display():
    """Test phase display string formatting."""
    state = OrchestratorState()
    display = state.get_phase_display()
    assert "[Phase 1/8]" in display
    assert "Classifying" in display


def test_can_transition_to():
    """Test the can_transition_to helper method."""
    state = OrchestratorState(strict_mode=True)

    # Without artifact, should report cannot transition
    can, error = state.can_transition_to(OrchestrationPhase.CONTEXT)
    assert not can
    assert "query_classification" in error

    # With artifact, should report can transition
    state.register_artifact("query_classification", "SEMANTIC")
    can, error = state.can_transition_to(OrchestrationPhase.CONTEXT)
    assert can
    assert error is None


def test_get_missing_artifacts():
    """Test the get_missing_artifacts helper method."""
    state = OrchestratorState()

    # CONTEXT requires query_classification
    missing = state.get_missing_artifacts(OrchestrationPhase.CONTEXT)
    assert "query_classification" in missing

    # After registering, should be empty
    state.register_artifact("query_classification", "PATTERN")
    missing = state.get_missing_artifacts(OrchestrationPhase.CONTEXT)
    assert len(missing) == 0


def test_reset():
    """Test state reset functionality."""
    state = OrchestratorState(strict_mode=False)
    state.transition_to(OrchestrationPhase.CONTEXT)
    state.register_artifact("test", "data")

    state.reset()

    assert state.current_phase == OrchestrationPhase.CLASSIFY
    assert len(state.history) == 0
    assert len(state.artifacts) == 0


def test_get_summary():
    """Test state summary generation."""
    state = OrchestratorState(strict_mode=False)
    state.register_artifact("query_classification", "SEMANTIC")
    state.transition_to(OrchestrationPhase.CONTEXT)

    summary = state.get_summary()

    assert summary["current_phase"] == "context"
    assert summary["phase_number"] == 2
    assert "classify" in summary["history"]
    assert "query_classification" in summary["artifacts"]
