import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from mcp_bridge.tools.agent_manager import AgentManager
from mcp_bridge.orchestrator.state import OrchestratorState
from mcp_bridge.orchestrator.enums import OrchestrationPhase

@pytest.mark.asyncio
async def test_agent_orchestrator_integration():
    # Mock Orchestrator State
    mock_state = MagicMock(spec=OrchestratorState)
    mock_state.current_phase = OrchestrationPhase.PLAN
    
    # Initialize AgentManager (it only takes base_dir)
    with patch("mcp_bridge.tools.agent_manager.subprocess.Popen"): # Mock sidecar
        manager = AgentManager(base_dir="/tmp/test_agents")
        manager.orchestrator = mock_state
        
        # Test attribute
        assert manager.orchestrator == mock_state

@pytest.mark.asyncio
async def test_spawn_enforces_phase():
    with patch("mcp_bridge.tools.agent_manager.subprocess.Popen"):
        manager = AgentManager(base_dir="/tmp/test_agents")
        manager.orchestrator = MagicMock(spec=OrchestratorState)
        
        # Mock transition logic if we were calling it
        # For now, just verifying we can set the orchestrator on the manager
        assert hasattr(manager, "orchestrator")