"""Test suite for Phase 3: Clean Output Formatting.

Tests cover:
- Clean output mode format (✓ agent:model → task_id)
- Character limit enforcement (under 100 chars)
- OutputMode enum
- Color-coded status (green=success, yellow=progress, red=failed)
- Silent and verbose modes
"""

import pytest
from mcp_bridge.tools.agent_manager import format_spawn_output, OutputMode
import re


# ============================================================================
# TESTS
# ============================================================================


def test_clean_output_format():
    """Test clean output format: ✓ agent:model → task_id."""
    output = format_spawn_output(
        agent_type="explore",
        display_model="gemini-3-flash",
        task_id="task_abc123",
        mode=OutputMode.CLEAN,
    )

    # Check format (strip ANSI codes for testing)
    plain_output = re.sub(r'\x1b\[[0-9;]*m', '', output)

    assert "✓" in plain_output
    assert "explore:gemini-3-flash" in plain_output
    assert "task_abc123" in plain_output
    assert "→" in plain_output


def test_clean_output_under_100_chars():
    """Test clean output is under 100 characters (excluding ANSI codes)."""
    output = format_spawn_output(
        agent_type="implementation-lead",
        display_model="claude-sonnet-4.5",
        task_id="task_xyz789_very_long_id",
        mode=OutputMode.CLEAN,
    )

    # Strip ANSI color codes for length check
    plain_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    assert len(plain_output) < 100, f"Output too long: {len(plain_output)} chars"


def test_silent_mode_returns_empty():
    """Test silent mode returns empty string."""
    output = format_spawn_output(
        agent_type="explore",
        display_model="gemini-3-flash",
        task_id="task_abc123",
        mode=OutputMode.SILENT,
    )

    assert output == ""


def test_verbose_mode():
    """Test verbose mode returns empty (handled by caller)."""
    output = format_spawn_output(
        agent_type="explore",
        display_model="gemini-3-flash",
        task_id="task_abc123",
        mode=OutputMode.VERBOSE,
    )

    # Verbose mode returns empty string, caller handles full formatting
    assert output == ""


def test_output_mode_enum_exists():
    """Test OutputMode enum has required values."""
    assert hasattr(OutputMode, 'CLEAN')
    assert hasattr(OutputMode, 'VERBOSE')
    assert hasattr(OutputMode, 'SILENT')

    assert OutputMode.CLEAN.value == 'clean'
    assert OutputMode.VERBOSE.value == 'verbose'
    assert OutputMode.SILENT.value == 'silent'


def test_format_with_different_agents():
    """Test formatting works for all agent types."""
    agent_types = ["explore", "dewey", "frontend", "delphi", "momus", "comment_checker"]

    for agent_type in agent_types:
        output = format_spawn_output(
            agent_type=agent_type,
            display_model="test-model",
            task_id="task_123",
            mode=OutputMode.CLEAN,
        )

        plain_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
        assert agent_type in plain_output
        assert "task_123" in plain_output


def test_ansi_colors_present():
    """Test that ANSI color codes are present in clean output."""
    output = format_spawn_output(
        agent_type="explore",
        display_model="gemini-3-flash",
        task_id="task_abc123",
        mode=OutputMode.CLEAN,
    )

    # Check for ANSI escape sequences
    assert '\x1b[' in output, "Output should contain ANSI color codes"


def test_format_consistency():
    """Test format is consistent across multiple calls."""
    outputs = [
        format_spawn_output("explore", "gemini-3-flash", "task_1", OutputMode.CLEAN)
        for _ in range(5)
    ]

    # Strip ANSI codes for comparison
    plain_outputs = [re.sub(r'\x1b\[[0-9;]*m', '', o) for o in outputs]

    # All outputs should be identical
    assert all(o == plain_outputs[0] for o in plain_outputs)
