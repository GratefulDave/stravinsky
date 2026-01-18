import pytest
from mcp_bridge.orchestrator.enums import OrchestrationPhase
from mcp_bridge.orchestrator.router import Router, ModelConfig

def test_model_selection():
    config = ModelConfig(
        planning_model="smart-model-v1",
        execution_model="fast-model-v1"
    )
    router = Router(config)
    
    # Planning phases should use smart model
    assert router.select_model(OrchestrationPhase.PLAN) == "smart-model-v1"
    assert router.select_model(OrchestrationPhase.VALIDATE) == "smart-model-v1"
    
    # Execution phases should use fast model
    assert router.select_model(OrchestrationPhase.EXECUTE) == "fast-model-v1"
    assert router.select_model(OrchestrationPhase.CONTEXT) == "fast-model-v1"

def test_default_fallback():
    router = Router() # Uses defaults
    # Should fallback to whatever default logic is (likely gemini-3-flash for both if not configured)
    assert router.select_model(OrchestrationPhase.PLAN) is not None
