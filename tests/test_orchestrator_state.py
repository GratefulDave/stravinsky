import pytest
from mcp_bridge.orchestrator.enums import OrchestrationPhase
from mcp_bridge.orchestrator.state import OrchestratorState

def test_phases_enum():
    assert OrchestrationPhase.CLASSIFY.value == "classify"
    assert OrchestrationPhase.CONTEXT.value == "context"
    assert OrchestrationPhase.WISDOM.value == "wisdom"
    assert OrchestrationPhase.PLAN.value == "plan"
    assert OrchestrationPhase.VALIDATE.value == "validate"
    assert OrchestrationPhase.DELEGATE.value == "delegate"
    assert OrchestrationPhase.EXECUTE.value == "execute"
    assert OrchestrationPhase.VERIFY.value == "verify"

def test_orchestrator_state_transitions():
    state = OrchestratorState()
    assert state.current_phase == OrchestrationPhase.CLASSIFY
    
    # Test valid transition
    state.transition_to(OrchestrationPhase.CONTEXT)
    assert state.current_phase == OrchestrationPhase.CONTEXT
    assert OrchestrationPhase.CLASSIFY in state.history

def test_required_artifacts():
    state = OrchestratorState()
    # Assume context phase requires no artifacts, but Plan does
    state.transition_to(OrchestrationPhase.PLAN)
    
    # Should fail transition to Validate if plan.md not registered
    with pytest.raises(ValueError, match="Missing artifact"):
        state.transition_to(OrchestrationPhase.VALIDATE)
        
    state.register_artifact("plan.md", "content")
    state.transition_to(OrchestrationPhase.VALIDATE)
    assert state.current_phase == OrchestrationPhase.VALIDATE
