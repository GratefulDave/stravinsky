"""
Visualization utilities for the 7-Phase Orchestrator.

Provides rich formatting for phase progress and agent execution with:
- ANSI color coding per agent type
- Multi-line formatted output
- Phase progress visualization
- Parallel agent batch grouping
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import TextIO

from .enums import OrchestrationPhase


class Color:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Agent colors
    BLUE = "\033[94m"  # explore
    PURPLE = "\033[95m"  # dewey, code-reviewer
    GREEN = "\033[92m"  # frontend
    ORANGE = "\033[93m"  # delphi
    RED = "\033[91m"  # debugger
    CYAN = "\033[96m"  # research-lead
    WHITE = "\033[97m"  # default

    # Phase colors
    PHASE_ACTIVE = "\033[96m"  # Cyan for active phase
    PHASE_COMPLETE = "\033[92m"  # Green for completed
    PHASE_PENDING = "\033[90m"  # Gray for pending


class AgentEmoji(Enum):
    """Emoji indicators for agent types."""

    EXPLORE = "🔵"
    DEWEY = "🟣"
    FRONTEND = "🟢"
    DELPHI = "🟠"
    DEBUGGER = "🔴"
    CODE_REVIEWER = "🟣"
    RESEARCH_LEAD = "🔷"
    IMPLEMENTATION_LEAD = "🟩"
    MOMUS = "⚪"
    DEFAULT = "⚪"


# Agent type to color/emoji mapping
AGENT_COLORS: dict[str, tuple[str, str]] = {
    "explore": (Color.BLUE, AgentEmoji.EXPLORE.value),
    "dewey": (Color.PURPLE, AgentEmoji.DEWEY.value),
    "frontend": (Color.GREEN, AgentEmoji.FRONTEND.value),
    "delphi": (Color.ORANGE, AgentEmoji.DELPHI.value),
    "debugger": (Color.RED, AgentEmoji.DEBUGGER.value),
    "code-reviewer": (Color.PURPLE, AgentEmoji.CODE_REVIEWER.value),
    "research-lead": (Color.CYAN, AgentEmoji.RESEARCH_LEAD.value),
    "implementation-lead": (Color.GREEN, AgentEmoji.IMPLEMENTATION_LEAD.value),
    "momus": (Color.WHITE, AgentEmoji.MOMUS.value),
}


def _supports_color() -> bool:
    """Check if the terminal supports ANSI colors."""
    # Respect NO_COLOR env var (https://no-color.org/)
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("STRAVINSKY_NO_COLOR"):
        return False

    # Check for color support
    if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
        return True

    # Check TERM environment variable
    term = os.environ.get("TERM", "")
    if "color" in term or "256" in term or "xterm" in term:
        return True

    return False


def _colorize(text: str, color: str) -> str:
    """Apply color to text if terminal supports it."""
    if _supports_color():
        return f"{color}{text}{Color.RESET}"
    return text


def format_phase_progress(current_phase: OrchestrationPhase) -> str:
    """
    Formats the current phase as a progress string with visual indicators.

    Example output: [Phase 3/8: WISDOM] ━━━●━━━━━

    Args:
        current_phase: The current orchestration phase

    Returns:
        Formatted progress string with phase indicator
    """
    phases = list(OrchestrationPhase)
    total = len(phases)

    # Find index (1-based)
    try:
        index = phases.index(current_phase) + 1
    except ValueError:
        index = 0

    # Build progress bar
    progress_chars = []
    for i in range(1, total + 1):
        if i < index:
            progress_chars.append(_colorize("━", Color.PHASE_COMPLETE))
        elif i == index:
            progress_chars.append(_colorize("●", Color.PHASE_ACTIVE))
        else:
            progress_chars.append(_colorize("─", Color.PHASE_PENDING))

    progress_bar = "".join(progress_chars)

    phase_text = _colorize(f"[Phase {index}/{total}: {current_phase.name}]", Color.BOLD)

    return f"{phase_text} {progress_bar}"


def display_agent_execution(
    agent_name: str,
    model_name: str,
    task_summary: str,
    output: TextIO | None = None,
) -> str:
    """
    Formats agent execution with rich color-coded output.

    Example output:
    🔵 EXPLORE → gemini-3-flash
       Task: Find authentication implementations in codebase

    Args:
        agent_name: Type of agent (explore, dewey, delphi, etc.)
        model_name: Model being used (gemini-3-flash, gpt-5.2, etc.)
        task_summary: Description of the task
        output: Optional TextIO for direct writing (defaults to return string)

    Returns:
        Formatted multi-line string for agent execution
    """
    # Get color and emoji for agent type
    agent_lower = agent_name.lower()
    color, emoji = AGENT_COLORS.get(agent_lower, (Color.WHITE, AgentEmoji.DEFAULT.value))

    # Clean up task summary (first line, reasonable length)
    summary_lines = task_summary.strip().split("\n")
    summary = summary_lines[0][:80] if summary_lines else "Task delegated"

    # Build formatted output
    agent_upper = agent_name.upper()
    header = _colorize(f"{emoji} {agent_upper} → {model_name}", color)
    task_line = f"   Task: {summary}"

    formatted = f"{header}\n{task_line}\n"

    if output:
        output.write(formatted)
        output.flush()

    return formatted


def display_parallel_batch_header(agent_count: int, output: TextIO | None = None) -> str:
    """
    Display a header for parallel agent batch execution.

    Example output:
    ══════════════════════════════════════════════════
    PARALLEL DELEGATION (3 agents)
    ══════════════════════════════════════════════════

    Args:
        agent_count: Number of agents being spawned in parallel
        output: Optional TextIO for direct writing

    Returns:
        Formatted batch header string
    """
    line = "═" * 50
    header = _colorize(f"\n{line}\nPARALLEL DELEGATION ({agent_count} agents)\n{line}\n", Color.BOLD)

    if output:
        output.write(header)
        output.flush()

    return header


@dataclass
class PhaseVisualization:
    """Visualization state for phase transitions."""

    current_phase: OrchestrationPhase
    completed_phases: list[OrchestrationPhase]
    pending_phases: list[OrchestrationPhase]

    def render(self) -> str:
        """Render the full phase visualization."""
        lines = []

        # Header
        lines.append(_colorize("7-Phase Orchestrator Status", Color.BOLD))
        lines.append("")

        # Phase list with status
        for phase in OrchestrationPhase:
            if phase in self.completed_phases:
                status = _colorize("✓", Color.PHASE_COMPLETE)
                name = _colorize(phase.name, Color.DIM)
            elif phase == self.current_phase:
                status = _colorize("►", Color.PHASE_ACTIVE)
                name = _colorize(phase.name, Color.BOLD)
            else:
                status = _colorize("○", Color.PHASE_PENDING)
                name = _colorize(phase.name, Color.DIM)

            lines.append(f"  {status} {name}")

        return "\n".join(lines)


def format_tool_routing(
    query: str,
    category: str,
    tool: str,
    confidence: float,
) -> str:
    """
    Format query classification routing information.

    Example output:
    🔍 Query: "Find authentication logic"
       Category: SEMANTIC (0.85)
       Tool: semantic_search

    Args:
        query: The original query
        category: Classification category (PATTERN, STRUCTURAL, SEMANTIC, HYBRID)
        tool: Suggested tool name
        confidence: Confidence score (0.0-1.0)

    Returns:
        Formatted routing information string
    """
    # Truncate long queries
    display_query = query[:60] + "..." if len(query) > 60 else query

    # Color code by category
    category_colors = {
        "PATTERN": Color.BLUE,
        "STRUCTURAL": Color.GREEN,
        "SEMANTIC": Color.PURPLE,
        "HYBRID": Color.ORANGE,
    }
    cat_color = category_colors.get(category.upper(), Color.WHITE)

    lines = [
        f'🔍 Query: "{display_query}"',
        f"   Category: {_colorize(category.upper(), cat_color)} ({confidence:.2f})",
        f"   Tool: {tool}",
    ]

    return "\n".join(lines)
