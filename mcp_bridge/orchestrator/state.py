from typing import List, Dict, Optional, Callable
from .enums import OrchestrationPhase

class OrchestratorState:
    def __init__(self, enable_phase_gates: bool = False, approver: Optional[Callable[[], bool]] = None):
        self.current_phase = OrchestrationPhase.CLASSIFY
        self.history: List[OrchestrationPhase] = []
        self.artifacts: Dict[str, str] = {}
        self.enable_phase_gates = enable_phase_gates
        self.approver = approver
        
    def transition_to(self, next_phase: OrchestrationPhase):
        """Transitions to the next phase if requirements are met."""
        self._validate_transition(next_phase)
        
        # Phase Gates
        if self.enable_phase_gates and self.approver:
            if not self.approver():
                raise PermissionError(f"Transition to {next_phase} denied by user.")
        
        self.history.append(self.current_phase)
        self.current_phase = next_phase
        
    def register_artifact(self, name: str, content: str):
        self.artifacts[name] = content
        
    def _validate_transition(self, next_phase: OrchestrationPhase):
        """Enforce strict phase requirements."""
        # Example: Must have plan before validation
        if next_phase == OrchestrationPhase.VALIDATE:
            if "plan.md" not in self.artifacts and self.current_phase == OrchestrationPhase.PLAN:
                raise ValueError("Missing artifact: plan.md is required to enter Validation phase")