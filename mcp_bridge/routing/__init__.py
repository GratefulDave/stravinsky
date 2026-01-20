"""
Stravinsky Multi-Provider Routing System.

This module provides intelligent routing between providers (Claude, OpenAI, Gemini)
with automatic fallback when providers hit rate limits or capacity constraints.

Components:
- ProviderState: Tracks availability of each provider
- ProviderStateTracker: Global state management for all providers
- TaskClassifier: Classifies tasks to route to optimal providers
- RoutingConfig: Project-local configuration loader
"""

from .config import (
    DEFAULT_ROUTING_CONFIG,
    RoutingConfig,
    load_routing_config,
)
from .provider_state import (
    ProviderState,
    ProviderStateTracker,
    get_provider_tracker,
)
from .task_classifier import (
    TaskType,
    classify_task,
    get_routing_for_task,
)

__all__ = [
    # Provider state
    "ProviderState",
    "ProviderStateTracker",
    "get_provider_tracker",
    # Task classification
    "TaskType",
    "classify_task",
    "get_routing_for_task",
    # Configuration
    "load_routing_config",
    "RoutingConfig",
    "DEFAULT_ROUTING_CONFIG",
]
