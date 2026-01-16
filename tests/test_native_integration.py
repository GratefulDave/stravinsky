import pytest
import sys

def test_native_module_import():
    try:
        import stravinsky_native
    except ImportError:
        pytest.fail("Could not import stravinsky_native module")
        
    assert stravinsky_native.sum_as_string(2, 3) == "5"

def test_native_module_structure():
    import stravinsky_native
    assert hasattr(stravinsky_native, "sum_as_string")
