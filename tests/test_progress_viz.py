import pytest
from mcp_bridge.orchestrator.enums import OrchestrationPhase
from mcp_bridge.orchestrator.visualization import format_phase_progress

def test_phase_visualization():
    assert "[Phase 1/8: CLASSIFY]" in format_phase_progress(OrchestrationPhase.CLASSIFY)
    assert "[Phase 4/8: PLAN]" in format_phase_progress(OrchestrationPhase.PLAN)
    assert "[Phase 8/8: VERIFY]" in format_phase_progress(OrchestrationPhase.VERIFY)
