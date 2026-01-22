import pytest
from unittest.mock import MagicMock
from mcp_bridge.orchestrator.state import OrchestratorState
from mcp_bridge.orchestrator.enums import OrchestrationPhase

def test_phase_gates_disabled():
    # strict_mode=False to skip artifact validation (testing phase gates, not artifacts)
    state = OrchestratorState(enable_phase_gates=False, strict_mode=False)
    # Should transition immediately
    state.transition_to(OrchestrationPhase.CONTEXT)
    assert state.current_phase == OrchestrationPhase.CONTEXT

def test_phase_gates_enabled_requires_approval():
    # Mocking user interaction is tricky in core state,
    # but let's assume we pass an `approver` callback.
    # strict_mode=False to skip artifact validation (testing phase gates, not artifacts)

    approver = MagicMock(return_value=True)
    state = OrchestratorState(enable_phase_gates=True, approver=approver, strict_mode=False)

    state.transition_to(OrchestrationPhase.CONTEXT)
    assert state.current_phase == OrchestrationPhase.CONTEXT
    approver.assert_called_once()

def test_phase_gates_enabled_denied():
    # strict_mode=False to skip artifact validation (testing phase gates, not artifacts)
    approver = MagicMock(return_value=False)
    state = OrchestratorState(enable_phase_gates=True, approver=approver, strict_mode=False)

    # Should raise error or stay in same phase
    with pytest.raises(PermissionError):
        state.transition_to(OrchestrationPhase.CONTEXT)

    assert state.current_phase == OrchestrationPhase.CLASSIFY
