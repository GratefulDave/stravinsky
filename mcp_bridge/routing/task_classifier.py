"""
Task Classifier for Intelligent Routing.

Classifies incoming tasks to determine the optimal provider and model.
Uses pattern matching and heuristics to categorize tasks.
"""

from __future__ import annotations

import logging
import re
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks for routing purposes."""

    CODE_GENERATION = auto()  # Creating new code
    CODE_REFACTORING = auto()  # Improving existing code structure
    DEBUGGING = auto()  # Fixing bugs and errors
    ARCHITECTURE = auto()  # System design and planning
    DOCUMENTATION = auto()  # Writing docs, comments, READMEs
    CODE_SEARCH = auto()  # Finding code patterns
    SECURITY_REVIEW = auto()  # Security analysis
    GENERAL = auto()  # Default fallback


# Patterns for task classification
TASK_PATTERNS: dict[TaskType, list[str]] = {
    TaskType.CODE_GENERATION: [
        r"\b(generate|create|implement|build|write|add|make|develop)\b.*\b(code|function|class|module|component|api|endpoint|feature)\b",
        r"\b(new|fresh)\b.*\b(implementation|feature|module)\b",
        r"\bimplement\b",
        r"\bcreate a\b",
    ],
    TaskType.CODE_REFACTORING: [
        r"\b(refactor|restructure|reorganize|clean\s*up|simplify|optimize|improve)\b",
        r"\b(extract|inline|rename|move)\b.*\b(method|function|class|variable)\b",
        r"\bcode\s*(cleanup|quality)\b",
        r"\breduce\s*(complexity|duplication)\b",
    ],
    TaskType.DEBUGGING: [
        r"\b(debug|fix|solve|resolve|troubleshoot|diagnose)\b",
        r"\b(bug|error|issue|problem|failing|broken|crash)\b",
        r"\b(not\s*working|doesn't\s*work|won't\s*work)\b",
        r"\b(exception|traceback|stack\s*trace)\b",
        r"\bwhy\s*(is|does|doesn't)\b.*\b(fail|error|crash)\b",
    ],
    TaskType.ARCHITECTURE: [
        r"\b(architect|design|structure|pattern|system)\b",
        r"\b(high\s*level|overall|big\s*picture)\b",
        r"\b(scalability|maintainability|extensibility)\b",
        r"\b(trade\s*off|decision|approach|strategy)\b",
        r"\bhow\s*should\s*(we|i)\s*(design|structure|organize)\b",
    ],
    TaskType.DOCUMENTATION: [
        r"\b(document|readme|docstring|comment|explain|describe)\b",
        r"\b(api\s*docs|documentation|jsdoc|pydoc)\b",
        r"\bwrite\s*(up|docs|documentation)\b",
        r"\badd\s*comments?\b",
    ],
    TaskType.CODE_SEARCH: [
        r"\b(find|search|locate|where\s*is|look\s*for)\b.*\b(code|function|class|implementation)\b",
        r"\b(grep|ripgrep|search)\b",
        r"\bhow\s*is\b.*\b(implemented|used|called)\b",
        r"\bshow\s*me\b.*\b(code|implementation)\b",
    ],
    TaskType.SECURITY_REVIEW: [
        r"\b(security|vulnerability|exploit|attack|injection)\b",
        r"\b(auth|authentication|authorization|permission)\b.*\b(check|review|audit)\b",
        r"\b(secure|harden|protect)\b",
        r"\b(xss|csrf|sql\s*injection|rce)\b",
    ],
}

# Default routing for each task type
DEFAULT_TASK_ROUTING: dict[TaskType, tuple[str, str | None]] = {
    TaskType.CODE_GENERATION: ("openai", "gpt-5-codex"),
    TaskType.CODE_REFACTORING: ("openai", "gpt-5-codex"),
    TaskType.DEBUGGING: ("openai", "gpt-5-codex"),
    TaskType.ARCHITECTURE: ("openai", "gpt-5.2-medium"),  # Delphi-style
    TaskType.DOCUMENTATION: ("gemini", "gemini-3-flash"),
    TaskType.CODE_SEARCH: ("gemini", "gemini-3-flash"),
    TaskType.SECURITY_REVIEW: ("claude", None),  # Keep in Claude
    TaskType.GENERAL: ("claude", None),  # Default to Claude
}


def classify_task(prompt: str, context: dict[str, Any] | None = None) -> TaskType:
    """
    Classify a task based on prompt content and optional context.

    Uses pattern matching against known task type indicators.

    Args:
        prompt: The user's prompt or request
        context: Optional context dict with additional signals

    Returns:
        TaskType enum indicating the classification
    """
    if not prompt:
        return TaskType.GENERAL

    prompt_lower = prompt.lower()

    # Check patterns for each task type
    # Priority order matters - first match wins
    priority_order = [
        TaskType.DEBUGGING,  # Most specific - error fixing
        TaskType.SECURITY_REVIEW,  # Security concerns
        TaskType.CODE_REFACTORING,  # Improvement tasks
        TaskType.ARCHITECTURE,  # Design decisions
        TaskType.DOCUMENTATION,  # Doc writing
        TaskType.CODE_SEARCH,  # Finding code
        TaskType.CODE_GENERATION,  # Creating code (broad)
    ]

    for task_type in priority_order:
        patterns = TASK_PATTERNS.get(task_type, [])
        for pattern in patterns:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                logger.debug(f"[TaskClassifier] Matched {task_type.name} with pattern: {pattern}")
                return task_type

    # Check context for additional signals
    if context:
        # If there's an error in context, likely debugging
        if context.get("error") or context.get("exception"):
            return TaskType.DEBUGGING

        # If there's existing code to modify
        if context.get("existing_code") and not context.get("create_new"):
            return TaskType.CODE_REFACTORING

    return TaskType.GENERAL


def get_routing_for_task(
    task_type: TaskType,
    config: dict[str, Any] | None = None,
) -> tuple[str, str | None]:
    """
    Get the recommended (provider, model) for a task type.

    Args:
        task_type: The classified task type
        config: Optional routing config override

    Returns:
        Tuple of (provider, model) where model may be None
    """
    # Use config if provided
    if config:
        task_name = task_type.name.lower()
        if task_name in config:
            rule = config[task_name]
            return (rule.get("provider", "claude"), rule.get("model"))

    # Fall back to defaults
    return DEFAULT_TASK_ROUTING.get(task_type, ("claude", None))


def classify_and_route(
    prompt: str,
    context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[TaskType, str, str | None]:
    """
    Classify a task and get routing recommendation in one call.

    Args:
        prompt: The user's prompt
        context: Optional context dict
        config: Optional routing config override

    Returns:
        Tuple of (task_type, provider, model)
    """
    task_type = classify_task(prompt, context)
    provider, model = get_routing_for_task(task_type, config)

    logger.info(
        f"[TaskClassifier] Classified as {task_type.name} → {provider}/{model or 'default'}"
    )

    return task_type, provider, model
