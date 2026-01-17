import pytest
import stravinsky_native

def test_chunk_code_python():
    content = """
def hello(name: str) -> str:
    '''Greets someone.'''
    # This is a comment to make it 3 lines
    return f"Hello, {name}"

class Greeter:
    def __init__(self, greeting: str):
        self.greeting = greeting
        # Another line
        pass
        
    def greet(self, name: str):
        print(f"{self.greeting}, {name}")
        # Make it 3 lines
        return True
"""
    chunks = stravinsky_native.chunk_code(content, "python")
    
    # hello (4 lines), Greeter (class), __init__ (4 lines), greet (3 lines)
    assert len(chunks) >= 4
    
    names = [c.get("name") for c in chunks]
    assert "hello" in names
    assert "Greeter" in names
    
    # Check metadata
    greet_chunk = next(c for c in chunks if c.get("name") == "hello")
    assert greet_chunk["start_line"] == 2
    assert "def hello" in greet_chunk["content"]
    assert greet_chunk["node_type"] == "func"

def test_chunk_code_typescript():
    content = """
export function add(a: number, b: number): number {
    return a + b;
}

class Calculator {
    multiply(a: number, b: number): number {
        return a * b;
    }
}
"""
    chunks = stravinsky_native.chunk_code(content, "typescript")
    
    assert len(chunks) >= 3
    names = [c.get("name") for c in chunks]
    assert "add" in names
    assert "Calculator" in names
    assert "multiply" in names

def test_chunk_code_unsupported():
    chunks = stravinsky_native.chunk_code("main() { }", "c")
    assert chunks == []
