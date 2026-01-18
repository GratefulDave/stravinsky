import pytest
import sys

# Try to import the native module. 
# In a real environment, this would be built and installed.
# For TDD "Red" phase, we expect this to fail if the module/functions don't exist.
try:
    import stravinsky_native
    from stravinsky_native import truncator
except ImportError:
    stravinsky_native = None
    truncator = None

@pytest.mark.skipif(stravinsky_native is None, reason="stravinsky_native not installed")
def test_auto_tail_logs():
    """Test auto-tailing of logs (keep head + tail)."""
    # Create a long log string (100 lines)
    lines = [f"Line {i}" for i in range(100)]
    content = "\n".join(lines)
    
    # Keep 5 lines head, 5 lines tail
    truncated = truncator.auto_tail(content, 5, 5)
    
    assert "Line 0" in truncated
    assert "Line 4" in truncated
    assert "Line 95" in truncated
    assert "Line 99" in truncated
    assert "Line 50" not in truncated # Middle should be gone
    assert "lines truncated" in truncated # Placeholder

@pytest.mark.skipif(stravinsky_native is None, reason="stravinsky_native not installed")
def test_smart_summary_list():
    """Test smart summarization of a list/search result."""
    # Simulate a long list of items
    items = [f"- Item {i}: Some description" for i in range(100)]
    content = "\n".join(items)
    
    # Max lines 10
    summary = truncator.smart_summary(content, 10)
    
    # Head(5) + Space + Msg + Space + Tail(5) = 13 lines
    assert len(summary.splitlines()) <= 14 
    assert "Item 0" in summary
    assert "Item 99" in summary # Should try to keep end if relevant
    assert "70 lines hidden" in summary or "truncated" in summary

def test_module_structure_exists():
    """Fails if truncator module is not exposed."""
    if stravinsky_native is None:
        pytest.fail("stravinsky_native module not found")
    
    if not hasattr(stravinsky_native, "truncator"):
        pytest.fail("truncator submodule not found in stravinsky_native")
