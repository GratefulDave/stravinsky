from dataclasses import dataclass
from typing import Optional
from .enums import OrchestrationPhase

@dataclass
class ModelConfig:
    planning_model: str = "gemini-3-pro" # Default smart
    execution_model: str = "gemini-3-flash" # Default fast

class Router:
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        
    def select_model(self, phase: OrchestrationPhase) -> str:
        """Selects the best model for the given phase."""
        if phase in [OrchestrationPhase.PLAN, OrchestrationPhase.VALIDATE, OrchestrationPhase.WISDOM, OrchestrationPhase.VERIFY]:
            return self.config.planning_model
        else:
            return self.config.execution_model
