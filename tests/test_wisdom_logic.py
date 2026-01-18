import pytest
import os
from unittest.mock import patch, mock_open
from mcp_bridge.orchestrator.wisdom import WisdomLoader, CritiqueGenerator

def test_wisdom_loader_exists():
    with patch("builtins.open", mock_open(read_data="# Wisdom\n- Don't do X.")) as mock_file:
        with patch("os.path.exists", return_value=True):
            loader = WisdomLoader()
            content = loader.load_wisdom()
            assert "Don't do X" in content

def test_wisdom_loader_missing():
    with patch("os.path.exists", return_value=False):
        loader = WisdomLoader()
        content = loader.load_wisdom()
        assert content == "" # Should return empty string gracefully

def test_critique_generator_template():
    generator = CritiqueGenerator()
    prompt = generator.generate_critique_prompt("My Plan")
    assert "CRITIQUE" in prompt
    assert "My Plan" in prompt
    assert "List 3 ways this plan could fail" in prompt
