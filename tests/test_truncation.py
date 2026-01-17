import pytest
from mcp_bridge.utils.truncation import truncate_output, TruncationStrategy

def test_no_truncation_needed():
    text = "Short text"
    limit = 100
    result = truncate_output(text, limit)
    assert result == text

def test_tail_truncation():
    text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    limit = 20 # characters
    result = truncate_output(text, limit, strategy=TruncationStrategy.TAIL)
    assert "[Output truncated." in result
    assert "Line 5" in result
    assert len(result) > 0

def test_middle_truncation():
    text = "Start block\n" + "Middle content\n" * 100 + "End block"
    limit = 50
    result = truncate_output(text, limit, strategy=TruncationStrategy.MIDDLE)
    assert "Start block" in result
    assert "End block" in result
    assert "[... content truncated ...]" in result

def test_truncation_with_guidance():
    text = "A" * 1000
    limit = 100
    result = truncate_output(text, limit)
    assert "Use offset/limit parameters to read specific parts" in result
