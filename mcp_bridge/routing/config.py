"""
Routing Configuration with Project-Local Priority.

Loads routing configuration from:
1. .stravinsky/routing.json (project-local - highest priority)
2. ~/.stravinsky/routing.json (user-global fallback)
3. Built-in defaults

This allows per-project customization of routing behavior.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

# Default routing configuration
DEFAULT_ROUTING_CONFIG: dict[str, Any] = {
    "routing": {
        "enabled": True,
        "task_routing": {
            "code_generation": {
                "provider": "claude",
                "model": "claude-4.5-opus",
                "tier": "premium",
            },
            "code_refactoring": {
                "provider": "claude",
                "model": "claude-4.5-sonnet",
                "tier": "standard",
            },
            "debugging": {
                "provider": "openai",
                "model": "gpt-5.2",
                "tier": "standard",
            },
            "architecture": {
                "provider": "openai",
                "model": "gpt-5.2",
                "tier": "standard",
            },
            "documentation": {
                "provider": "gemini",
                "model": "gemini-3-flash-preview",
                "tier": "standard",
            },
            "code_search": {
                "provider": "gemini",
                "model": "gemini-3-flash-preview",
                "tier": "standard",
            },
            "security_review": {
                "provider": "claude",
                "model": "claude-4.5-opus",
                "tier": "premium",
            },
            "general": {
                "provider": "claude",
                "model": "claude-4.5-sonnet",
                "tier": "standard",
            },
        },
        "fallback": {
            "enabled": True,
            "chain": ["claude", "openai", "gemini"],
            "cooldown_seconds": 300,
        },
        "claude_limits": {
            "detection_enabled": True,
            "slow_response_threshold_seconds": 30,
            "auto_fallback": True,
        },
    }
}


@dataclass
class TaskRoutingRule:
    """Routing rule for a specific task type."""

    provider: str
    model: str | None = None
    tier: Literal["premium", "standard"] = "standard"


@dataclass
class FallbackConfig:
    """Fallback configuration."""

    enabled: bool = True
    chain: list[str] = field(default_factory=lambda: ["claude", "openai", "gemini"])
    cooldown_seconds: int = 300


@dataclass
class ClaudeLimitsConfig:
    """Claude limits detection configuration."""

    detection_enabled: bool = True
    slow_response_threshold_seconds: int = 30
    auto_fallback: bool = True


@dataclass
class RoutingConfig:
    """Complete routing configuration."""

    enabled: bool = True
    task_routing: dict[str, TaskRoutingRule] = field(default_factory=dict)
    fallback: FallbackConfig = field(default_factory=FallbackConfig)
    claude_limits: ClaudeLimitsConfig = field(default_factory=ClaudeLimitsConfig)
    source: str = "default"  # Where config was loaded from

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str = "dict") -> RoutingConfig:
        """Create RoutingConfig from a dictionary."""
        routing = data.get("routing", data)  # Handle both wrapped and unwrapped

        # Parse task routing
        task_routing = {}
        for task_type, rule in routing.get("task_routing", {}).items():
            if isinstance(rule, dict):
                task_routing[task_type] = TaskRoutingRule(
                    provider=rule.get("provider", "claude"),
                    model=rule.get("model"),
                )

        # Parse fallback config
        fallback_data = routing.get("fallback", {})
        fallback = FallbackConfig(
            enabled=fallback_data.get("enabled", True),
            chain=fallback_data.get("chain", ["claude", "openai", "gemini"]),
            cooldown_seconds=fallback_data.get("cooldown_seconds", 300),
        )

        # Parse claude limits config
        claude_data = routing.get("claude_limits", {})
        claude_limits = ClaudeLimitsConfig(
            detection_enabled=claude_data.get("detection_enabled", True),
            slow_response_threshold_seconds=claude_data.get("slow_response_threshold_seconds", 30),
            auto_fallback=claude_data.get("auto_fallback", True),
        )

        return cls(
            enabled=routing.get("enabled", True),
            task_routing=task_routing,
            fallback=fallback,
            claude_limits=claude_limits,
            source=source,
        )

    def get_routing_for_task(self, task_type: str) -> TaskRoutingRule:
        """Get routing rule for a task type, with fallback to general."""
        if task_type in self.task_routing:
            return self.task_routing[task_type]
        if "general" in self.task_routing:
            return self.task_routing["general"]
        return TaskRoutingRule(provider="claude", model=None)


def load_routing_config(project_path: str = ".") -> RoutingConfig:
    """
    Load routing config with project-local priority.

    Discovery order:
    1. .stravinsky/routing.json (project-local)
    2. ~/.stravinsky/routing.json (user-global)
    3. Built-in defaults

    Args:
        project_path: Path to the project root

    Returns:
        RoutingConfig instance
    """
    # Project-local config
    project_config_path = Path(project_path) / ".stravinsky" / "routing.json"
    if project_config_path.exists():
        try:
            data = json.loads(project_config_path.read_text())
            config = RoutingConfig.from_dict(data, source=str(project_config_path))
            logger.info(f"[RoutingConfig] Loaded project-local config from {project_config_path}")
            return config
        except Exception as e:
            logger.warning(f"[RoutingConfig] Failed to load {project_config_path}: {e}")

    # User-global fallback
    global_config_path = Path.home() / ".stravinsky" / "routing.json"
    if global_config_path.exists():
        try:
            data = json.loads(global_config_path.read_text())
            config = RoutingConfig.from_dict(data, source=str(global_config_path))
            logger.info(f"[RoutingConfig] Loaded user-global config from {global_config_path}")
            return config
        except Exception as e:
            logger.warning(f"[RoutingConfig] Failed to load {global_config_path}: {e}")

    # Built-in defaults
    logger.info("[RoutingConfig] Using built-in defaults")
    return RoutingConfig.from_dict(DEFAULT_ROUTING_CONFIG, source="default")


def init_routing_config(project_path: str = ".") -> Path:
    """
    Initialize a project-local routing config file.

    Creates .stravinsky/routing.json with default configuration.

    Args:
        project_path: Path to the project root

    Returns:
        Path to the created config file
    """
    config_dir = Path(project_path) / ".stravinsky"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "routing.json"

    if config_path.exists():
        logger.warning(f"[RoutingConfig] Config already exists at {config_path}")
        return config_path

    config_path.write_text(json.dumps(DEFAULT_ROUTING_CONFIG, indent=2))
    logger.info(f"[RoutingConfig] Created config at {config_path}")

    return config_path


def get_config_source(project_path: str = ".") -> str:
    """
    Get the source of the active routing config.

    Returns:
        Path to the config file being used, or "default" for built-in
    """
    project_config = Path(project_path) / ".stravinsky" / "routing.json"
    if project_config.exists():
        return str(project_config)

    global_config = Path.home() / ".stravinsky" / "routing.json"
    if global_config.exists():
        return str(global_config)

    return "default"
