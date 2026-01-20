from dataclasses import dataclass

from ..routing.config import load_routing_config
from ..routing.provider_state import get_provider_tracker
from ..routing.task_classifier import TaskType, classify_and_route
from ..routing.model_tiers import get_oauth_fallback_chain
from .enums import OrchestrationPhase


@dataclass
class ModelConfig:
    planning_model: str = "gemini-3-pro"  # Default smart
    execution_model: str = "gemini-3-flash"  # Default fast


class Router:
    """
    Intelligent model router with multi-provider fallback and task-based routing.

    Features:
    - Automatic fallback when providers hit rate limits
    - Task-based routing to optimal models (code gen → OpenAI, docs → Gemini)
    - Provider state tracking with cooldown management
    - Project-local configuration support
    """

    def __init__(self, config: ModelConfig | None = None, project_path: str = "."):
        self.config = config or ModelConfig()
        self.project_path = project_path

        # Load routing configuration
        self.routing_config = load_routing_config(project_path)

        # Get provider state tracker singleton
        self.provider_tracker = get_provider_tracker()

    def select_model(
        self,
        phase: OrchestrationPhase,
        task_type: TaskType | None = None,
        prompt: str | None = None,
    ) -> str:
        """
        Selects the best model for the given phase and task type.

        Args:
            phase: Orchestration phase (PLAN, EXECUTE, etc.)
            task_type: Optional task type override (CODE_GENERATION, DEBUGGING, etc.)
            prompt: Optional prompt text for automatic task classification

        Returns:
            Model identifier string (e.g., "gemini-3-flash", "gpt-5.2-codex")
        """
        # If task_type is provided or can be inferred, use task-based routing
        if task_type or prompt:
            # classify_and_route returns (TaskType, provider, model) tuple
            # Extract just the TaskType
            if task_type:
                inferred_type = task_type
            else:
                # classify_and_route returns tuple: (TaskType, provider, model)
                classification_result = classify_and_route(prompt or "")
                inferred_type = classification_result[0]  # Extract TaskType from tuple

            model = self._select_by_task_type(inferred_type)

            # Check provider availability and fallback if needed
            return self._check_availability_and_fallback(model, inferred_type)

        # Fallback to phase-based routing (legacy behavior)
        if phase in [
            OrchestrationPhase.PLAN,
            OrchestrationPhase.VALIDATE,
            OrchestrationPhase.WISDOM,
            OrchestrationPhase.VERIFY,
        ]:
            model = self.config.planning_model
        else:
            model = self.config.execution_model

        return self._check_availability_and_fallback(model, None)

    def _select_by_task_type(self, task_type: TaskType) -> str:
        """
        Select model based on task type using routing config.

        Args:
            task_type: Classified task type

        Returns:
            Primary model for this task type
        """
        # Look up task routing rule in config (it's a dict[str, TaskRoutingRule])
        task_name = task_type.name.lower()
        if task_name in self.routing_config.task_routing:
            rule = self.routing_config.task_routing[task_name]
            if rule.model:
                return rule.model

        # Fallback to default execution model if no rule matches
        return self.config.execution_model

    def _check_availability_and_fallback(self, model: str, task_type: TaskType | None) -> str:
        """
        Check provider availability and apply fallback if rate-limited.

        Args:
            model: Desired model
            task_type: Task type (for finding appropriate fallback)

        Returns:
            Available model (original or fallback)
        """
        # Determine provider from model name
        provider = self._get_provider_from_model(model)

        # Check provider availability using is_available() method
        if self.provider_tracker.is_available(provider):
            return model

        # Prefer tier-aware OAuth fallback chain when possible.
        # Note: use_oauth=False candidates represent non-OAuth access
        # (currently meaningful for Gemini API key fallback).
        try:
            oauth_chain = get_oauth_fallback_chain(provider, model)
        except ValueError:
            oauth_chain = []

        for candidate_provider, candidate_model, use_oauth in oauth_chain:
            if not use_oauth and candidate_provider == "gemini":
                return candidate_model
            if self.provider_tracker.is_available(candidate_provider):
                return candidate_model

        # Provider unavailable - use global fallback chain (legacy)
        # NOTE: Task-specific fallbacks from routing config are not currently
        # implemented (TaskRoutingRule doesn't have fallback_models field)
        for fallback_provider in self.routing_config.fallback.chain:
            if self.provider_tracker.is_available(fallback_provider):
                # Map provider to default model
                return self._get_default_model_for_provider(fallback_provider)

        # All providers unavailable - return original model and let caller handle error
        return model

    def _get_provider_from_model(self, model: str) -> str:
        """Extract provider name from model identifier."""
        if "gemini" in model.lower():
            return "gemini"
        elif "gpt" in model.lower() or "openai" in model.lower():
            return "openai"
        elif "claude" in model.lower():
            return "claude"
        else:
            # Default to gemini for unknown models
            return "gemini"

    def _get_default_model_for_provider(self, provider: str) -> str:
        """Get default model for a provider."""
        defaults = {
            "gemini": "gemini-3-flash",
            "openai": "gpt-5.2-codex",
            "claude": "claude-sonnet-4.5",
        }
        return defaults.get(provider, "gemini-3-flash")
