"""
Orchestrator State Machine - 7-Phase Workflow

Manages the orchestration lifecycle for Stravinsky agents:
1. CLASSIFY - Query classification and scope definition
2. CONTEXT - Gather codebase context using appropriate search strategy
3. WISDOM - Inject project wisdom from .stravinsky/wisdom.md
4. PLAN - Strategic planning with critique loop
5. VALIDATE - Validate plan against rules and constraints
6. DELEGATE - Route to appropriate models/agents
7. EXECUTE - Execute the plan
8. VERIFY - Verify results and synthesize output
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from collections.abc import Callable

from .enums import OrchestrationPhase

logger = logging.getLogger(__name__)


# =============================================================================
# PHASE REQUIREMENTS & VALID TRANSITIONS
# =============================================================================

# Artifacts required to ENTER each phase (checked during transition)
PHASE_REQUIREMENTS: dict[OrchestrationPhase, list[str]] = {
    OrchestrationPhase.CLASSIFY: [],  # Entry point, no requirements
    OrchestrationPhase.CONTEXT: ["query_classification"],  # Must classify first
    OrchestrationPhase.WISDOM: ["context_summary"],  # Must gather context first
    OrchestrationPhase.PLAN: [],  # Wisdom is optional (may not exist)
    OrchestrationPhase.VALIDATE: ["plan.md"],  # Must have a plan to validate
    OrchestrationPhase.DELEGATE: ["validation_result"],  # Must validate plan first
    OrchestrationPhase.EXECUTE: ["delegation_targets", "task_graph"],  # Must have task graph for parallel enforcement
    OrchestrationPhase.VERIFY: ["execution_result"],  # Must have executed something
}

# Valid phase transitions (from -> list of valid destinations)
VALID_TRANSITIONS: dict[OrchestrationPhase, list[OrchestrationPhase]] = {
    OrchestrationPhase.CLASSIFY: [OrchestrationPhase.CONTEXT],
    OrchestrationPhase.CONTEXT: [OrchestrationPhase.WISDOM, OrchestrationPhase.PLAN],  # Wisdom optional
    OrchestrationPhase.WISDOM: [OrchestrationPhase.PLAN],
    OrchestrationPhase.PLAN: [OrchestrationPhase.VALIDATE, OrchestrationPhase.PLAN],  # Can loop for critique
    OrchestrationPhase.VALIDATE: [OrchestrationPhase.DELEGATE, OrchestrationPhase.PLAN],  # Can go back to plan
    OrchestrationPhase.DELEGATE: [OrchestrationPhase.EXECUTE],
    OrchestrationPhase.EXECUTE: [OrchestrationPhase.VERIFY, OrchestrationPhase.EXECUTE],  # Can loop for retries
    OrchestrationPhase.VERIFY: [OrchestrationPhase.CLASSIFY],  # Can start new cycle
}

# Human-readable phase descriptions for UX
PHASE_DESCRIPTIONS: dict[OrchestrationPhase, str] = {
    OrchestrationPhase.CLASSIFY: "Classifying query and defining scope",
    OrchestrationPhase.CONTEXT: "Gathering codebase context",
    OrchestrationPhase.WISDOM: "Injecting project wisdom",
    OrchestrationPhase.PLAN: "Creating strategic plan",
    OrchestrationPhase.VALIDATE: "Validating plan against rules",
    OrchestrationPhase.DELEGATE: "Routing to appropriate agents",
    OrchestrationPhase.EXECUTE: "Executing the plan",
    OrchestrationPhase.VERIFY: "Verifying results",
}


@dataclass
class PhaseTransitionEvent:
    """Record of a phase transition for audit trail."""

    from_phase: OrchestrationPhase
    to_phase: OrchestrationPhase
    timestamp: str
    artifacts_present: list[str]
    success: bool
    error: str | None = None


@dataclass
class OrchestratorState:
    """
    Central state machine for 7-phase orchestration workflow.

    Enforces strict phase requirements and valid transitions.
    Supports optional phase gates requiring user approval.
    """

    current_phase: OrchestrationPhase = OrchestrationPhase.CLASSIFY
    history: list[OrchestrationPhase] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    transition_log: list[PhaseTransitionEvent] = field(default_factory=list)
    enable_phase_gates: bool = False
    approver: Callable[[], bool] | None = None
    strict_mode: bool = True  # If True, enforce artifact requirements
    critique_count: int = 0  # Track plan critique iterations
    max_critiques: int = 3  # Max critique loops before forcing forward

    def transition_to(self, next_phase: OrchestrationPhase) -> bool:
        """
        Transition to the next phase if requirements are met.

        Args:
            next_phase: The phase to transition to

        Returns:
            True if transition succeeded

        Raises:
            ValueError: If transition is invalid or requirements not met
            PermissionError: If phase gate denies the transition
        """
        event = PhaseTransitionEvent(
            from_phase=self.current_phase,
            to_phase=next_phase,
            timestamp=datetime.now().isoformat(),
            artifacts_present=list(self.artifacts.keys()),
            success=False,
        )

        try:
            # Validate the transition
            self._validate_transition(next_phase)

            # Check phase gates
            if self.enable_phase_gates and self.approver:
                if not self.approver():
                    raise PermissionError(f"Transition to {next_phase} denied by user.")

            # Record successful transition
            self.history.append(self.current_phase)
            self.current_phase = next_phase
            event.success = True

            # Track critique loops
            if next_phase == OrchestrationPhase.PLAN and self.history[-1] == OrchestrationPhase.VALIDATE:
                self.critique_count += 1
            elif next_phase != OrchestrationPhase.PLAN:
                self.critique_count = 0

            logger.info(f"[Orchestrator] Phase transition: {event.from_phase.value} → {next_phase.value}")
            return True

        except (ValueError, PermissionError) as e:
            event.error = str(e)
            logger.warning(f"[Orchestrator] Transition failed: {e}")
            raise
        finally:
            self.transition_log.append(event)

    def register_artifact(self, name: str, content: str) -> None:
        """
        Register an artifact for phase validation.

        Args:
            name: Artifact identifier (e.g., "plan.md", "query_classification")
            content: Artifact content
        """
        self.artifacts[name] = content
        logger.debug(f"[Orchestrator] Registered artifact: {name} ({len(content)} chars)")

    def has_artifact(self, name: str) -> bool:
        """Check if an artifact exists."""
        return name in self.artifacts

    def get_artifact(self, name: str) -> str | None:
        """Get an artifact by name."""
        return self.artifacts.get(name)

    def get_phase_number(self) -> int:
        """Get the current phase number (1-8)."""
        phases = list(OrchestrationPhase)
        return phases.index(self.current_phase) + 1

    def get_phase_display(self) -> str:
        """Get formatted phase display string for UX."""
        phase_num = self.get_phase_number()
        total_phases = len(OrchestrationPhase)
        description = PHASE_DESCRIPTIONS.get(self.current_phase, "")
        return f"[Phase {phase_num}/{total_phases}] {description}"

    def can_transition_to(self, next_phase: OrchestrationPhase) -> tuple[bool, str | None]:
        """
        Check if transition is possible without actually transitioning.

        Returns:
            Tuple of (can_transition, error_message)
        """
        try:
            self._validate_transition(next_phase)
            return True, None
        except ValueError as e:
            return False, str(e)

    def get_missing_artifacts(self, phase: OrchestrationPhase) -> list[str]:
        """Get list of missing artifacts required for a phase."""
        required = PHASE_REQUIREMENTS.get(phase, [])
        return [art for art in required if art not in self.artifacts]

    def _validate_transition(self, next_phase: OrchestrationPhase) -> None:
        """
        Enforce strict phase requirements and valid transitions.

        Args:
            next_phase: The target phase

        Raises:
            ValueError: If transition is invalid
        """
        # Check valid transitions
        valid_next = VALID_TRANSITIONS.get(self.current_phase, [])
        if next_phase not in valid_next:
            raise ValueError(
                f"Invalid transition: {self.current_phase.value} → {next_phase.value}. "
                f"Valid transitions: {[p.value for p in valid_next]}"
            )

        # Check artifact requirements (if strict mode enabled)
        if self.strict_mode:
            required_artifacts = PHASE_REQUIREMENTS.get(next_phase, [])
            missing = [art for art in required_artifacts if art not in self.artifacts]
            if missing:
                raise ValueError(
                    f"Missing artifacts for {next_phase.value} phase: {missing}. "
                    f"Available: {list(self.artifacts.keys())}"
                )

        # Special validation: max critique loops
        if next_phase == OrchestrationPhase.PLAN and self.current_phase == OrchestrationPhase.VALIDATE:
            if self.critique_count >= self.max_critiques:
                raise ValueError(
                    f"Max critique iterations ({self.max_critiques}) reached. "
                    f"Must proceed to DELEGATE phase."
                )

    def reset(self) -> None:
        """Reset state machine to initial state."""
        self.current_phase = OrchestrationPhase.CLASSIFY
        self.history.clear()
        self.artifacts.clear()
        self.transition_log.clear()
        self.critique_count = 0
        logger.info("[Orchestrator] State reset to CLASSIFY phase")

    def get_summary(self) -> dict:
        """Get a summary of the current orchestrator state."""
        return {
            "current_phase": self.current_phase.value,
            "phase_display": self.get_phase_display(),
            "phase_number": self.get_phase_number(),
            "total_phases": len(OrchestrationPhase),
            "history": [p.value for p in self.history],
            "artifacts": list(self.artifacts.keys()),
            "critique_count": self.critique_count,
            "strict_mode": self.strict_mode,
            "phase_gates_enabled": self.enable_phase_gates,
            "transitions_count": len(self.transition_log),
        }