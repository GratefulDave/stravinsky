#!/usr/bin/env python3
"""
Test script for continuation loop Stop hook.

Tests:
1. Loop activation with valid state file
2. Iteration counter increment
3. Max iterations termination
4. Completion promise detection
5. Active flag control
"""

import json
import sys
import tempfile
from pathlib import Path
import subprocess


def create_test_state(tmp_dir: Path, **kwargs):
    """Create a test state file with given parameters."""
    state_file = tmp_dir / ".stravinsky" / "continuation-loop.md"
    state_file.parent.mkdir(parents=True, exist_ok=True)

    defaults = {
        "iteration_count": 1,
        "max_iterations": 10,
        "completion_promise": "Goal completed",
        "active": True
    }
    defaults.update(kwargs)

    content = f"""---
iteration_count: {defaults['iteration_count']}
max_iterations: {defaults['max_iterations']}
completion_promise: "{defaults['completion_promise']}"
active: {str(defaults['active']).lower()}
---

Test context
"""
    state_file.write_text(content)
    return state_file


def run_hook(hook_path: Path, response_text: str, cwd: Path) -> tuple[int, str]:
    """Run the Stop hook with given response text."""
    hook_input = json.dumps({
        "response": response_text,
        "content": response_text,
        "message": response_text
    })

    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=hook_input,
        capture_output=True,
        text=True,
        cwd=str(cwd)
    )

    return result.returncode, result.stderr


def test_loop_activation():
    """Test 1: Loop activates with valid state file."""
    print("Test 1: Loop activation with valid state file...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        state_file = create_test_state(tmp_path, iteration_count=1, max_iterations=10)
        hook_path = Path(__file__).parent.parent / ".claude" / "hooks" / "stop_hook.py"

        exit_code, stderr = run_hook(hook_path, "Still working on it...", tmp_path)

        assert exit_code == 2, f"Expected exit code 2 (continue), got {exit_code}"
        assert "CONTINUATION LOOP ACTIVE" in stderr, "Missing continuation prompt"

        # Check iteration incremented
        content = state_file.read_text()
        assert "iteration_count: 2" in content, "Iteration count not incremented"

        print("✅ PASS: Loop activates and increments counter")


def test_max_iterations():
    """Test 2: Loop stops at max iterations."""
    print("\nTest 2: Max iterations termination...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Start at 8, so: 8+1=9 (continue), 9+1=10 (stop at 10 >= 10)
        state_file = create_test_state(tmp_path, iteration_count=8, max_iterations=10)
        hook_path = Path(__file__).parent.parent / ".claude" / "hooks" / "stop_hook.py"

        # First call: 8 -> 9, should continue (9 < 10)
        exit_code, stderr = run_hook(hook_path, "Still working...", tmp_path)
        assert exit_code == 2, f"Expected continue at iteration 8->9, got exit {exit_code}"

        # Second call: 9 -> 10, should stop (10 >= 10)
        exit_code, stderr = run_hook(hook_path, "Still working...", tmp_path)
        assert exit_code == 0, f"Expected stop at max iterations, got exit {exit_code}"
        assert "Max iterations" in stderr, "Missing max iterations message"
        assert not state_file.exists(), "State file not cleaned up"

        print("✅ PASS: Loop stops at max iterations")


def test_completion_promise():
    """Test 3: Loop stops when completion promise detected."""
    print("\nTest 3: Completion promise detection...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        state_file = create_test_state(
            tmp_path,
            iteration_count=3,
            max_iterations=10,
            completion_promise="All tests passing"
        )
        hook_path = Path(__file__).parent.parent / ".claude" / "hooks" / "stop_hook.py"

        # Response contains completion promise
        exit_code, stderr = run_hook(
            hook_path,
            "Great news! All tests passing and feature is complete.",
            tmp_path
        )

        assert exit_code == 0, f"Expected stop on completion promise, got exit {exit_code}"
        assert "Completion promise detected" in stderr, "Missing completion message"
        assert not state_file.exists(), "State file not cleaned up"

        print("✅ PASS: Loop stops on completion promise detection")


def test_active_flag():
    """Test 4: Loop stops when active=false."""
    print("\nTest 4: Active flag control...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        state_file = create_test_state(tmp_path, iteration_count=2, active=False)
        hook_path = Path(__file__).parent.parent / ".claude" / "hooks" / "stop_hook.py"

        exit_code, stderr = run_hook(hook_path, "Working on it...", tmp_path)

        assert exit_code == 0, f"Expected stop when active=false, got exit {exit_code}"

        print("✅ PASS: Loop stops when active=false")


def test_no_state_file():
    """Test 5: Hook passes through when no state file exists."""
    print("\nTest 5: No state file (normal operation)...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        hook_path = Path(__file__).parent.parent / ".claude" / "hooks" / "stop_hook.py"

        exit_code, stderr = run_hook(hook_path, "Normal response", tmp_path)

        assert exit_code == 0, f"Expected pass-through (exit 0), got {exit_code}"

        print("✅ PASS: Hook passes through when no state file")


def test_case_insensitive_promise():
    """Test 6: Completion promise is case-insensitive."""
    print("\nTest 6: Case-insensitive completion promise...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        state_file = create_test_state(
            tmp_path,
            completion_promise="Goal Completed"
        )
        hook_path = Path(__file__).parent.parent / ".claude" / "hooks" / "stop_hook.py"

        # Test lowercase match
        exit_code, stderr = run_hook(hook_path, "The goal completed successfully!", tmp_path)

        assert exit_code == 0, "Case-insensitive match should trigger completion"

        print("✅ PASS: Completion promise is case-insensitive")


if __name__ == "__main__":
    print("=" * 60)
    print("CONTINUATION LOOP STOP HOOK - TEST SUITE")
    print("=" * 60)

    try:
        test_loop_activation()
        test_max_iterations()
        test_completion_promise()
        test_active_flag()
        test_no_state_file()
        test_case_insensitive_promise()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
