import pytest
from mcp_bridge.utils.truncation import truncate_output, TruncationStrategy, auto_tail_logs

def test_auto_tail_logs_integration():
    """Test that auto_tail_logs uses the native implementation."""
    # 100 lines
    content = "\n".join([f"Line {i}" for i in range(100)])
    
    # Keep 5 lines head, 5 lines tail
    # This function doesn't exist yet in truncation.py
    result = auto_tail_logs(content, head_lines=5, tail_lines=5)
    
    assert "Line 0" in result
    assert "Line 4" in result
    assert "Line 95" in result
    assert "Line 99" in result
    # Check for native format
    assert "lines truncated" in result
