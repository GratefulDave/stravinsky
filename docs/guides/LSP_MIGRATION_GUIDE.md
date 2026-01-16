# LSP Migration Guide: From CLI-Shim to Persistent Servers

## 1. Introduction

This document outlines the transition of the `mcp_bridge` LSP implementation from a **CLI-Shim pattern** (short-lived subprocesses) to a **Persistent Server architecture** (long-lived JSON-RPC processes).

### Why Migrate?

*   **Performance:** Eliminates the overhead of spawning a new Python interpreter and re-indexing files for every single tool call.
*   **Consistency:** Leverages the official Language Server Protocol (LSP) instead of ad-hoc scripts, ensuring better compatibility with language-specific nuances.
*   **Feature Richness:** Enables advanced features like workspace-wide symbol searching and complex refactors that require cross-file state.
*   **Resource Efficiency:** Reduces CPU spikes caused by frequent process initialization.

### When to Migrate vs Keep CLI-Shim

**Migrate for:**
*   Standard IDE operations (Hover, Definition, References, Rename) in supported languages (Python, TypeScript)
*   Operations that benefit from cached state (workspace-wide searches, cross-file refactoring)
*   High-frequency tool calls in interactive workflows

**Keep CLI-Shim for:**
*   One-off tools or languages without a stable LSP implementation
*   Tools that don't benefit from state (e.g., simple regex-based linters like ruff)
*   Temporary workarounds during migration testing

### Target Audience

This guide is for developers working on the Stravinsky MCP bridge who need to:
- Understand the architectural shift from subprocess-based to persistent LSP servers
- Migrate existing LSP tools to use LSPManager
- Implement new LSP features using the persistent server pattern

---

## 2. Architecture Comparison

### Side-by-Side Comparison

| Feature | CLI-Shim (Current) | Persistent Server (New) |
|:--------|:-------------------|:------------------------|
| **Lifecycle** | Spawns/Kills process per request | Single process per language |
| **Latency** | High (200ms - 1s+ per call) | Low (<20ms per call) |
| **Communication** | `subprocess.run` + stdout parsing | JSON-RPC over stdio |
| **State** | Stateless (re-reads files every time) | Stateful (caches ASTs and indices) |
| **Resource Usage** | High CPU (bursty), Low RAM | Low CPU, Moderate RAM (persistent) |
| **Error Handling** | Subprocess timeouts/exit codes | JSON-RPC error codes & crash recovery |
| **Initialization** | Per-request (expensive) | Once on first use (lazy) |

### Performance Implications

**CLI-Shim Pattern:**
```
Request → Spawn Python → Import jedi → Parse file → Run operation → Parse stdout → Kill process
Time: ~450ms for simple hover
```

**Persistent Server Pattern:**
```
First Request → Start LSP server → Initialize → Cache AST → Run operation
Time: ~800ms startup + ~15ms per operation

Subsequent Requests → Run operation (use cached state)
Time: ~15ms per operation
```

### Resource Usage Comparison

**CLI-Shim:**
- CPU: High spikes per request (process spawning overhead)
- Memory: Low when idle (0 MB), transient during requests
- Disk I/O: High (re-reads files on every call)

**Persistent Server:**
- CPU: Low, steady (server runs in background)
- Memory: Moderate when active (~40-100 MB depending on workspace size)
- Disk I/O: Low (files cached in memory after first read)

### Error Handling Differences

**CLI-Shim Errors:**
```python
try:
    result = subprocess.run([...], timeout=10)
    if result.returncode != 0:
        return f"Error: {result.stderr}"
except subprocess.TimeoutExpired:
    return "Operation timed out"
except FileNotFoundError:
    return "jedi not installed"
```

**Persistent Server Errors:**
```python
try:
    response = await client.protocol.send_request_async(method, params)
except asyncio.TimeoutError:
    # Server hung, restart with backoff
    await manager._restart_with_backoff(server)
except ConnectionError:
    # Server crashed, fallback to CLI
    return await fallback_implementation()
```

---

## 3. Migration Examples

### Example A: `lsp_hover`

**Before (CLI-Shim) - Line 48-109 of tools.py:**

```python
async def lsp_hover(file_path: str, line: int, character: int) -> str:
    """Get type info at a position."""
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    lang = _get_language_for_file(file_path)

    try:
        if lang == "python":
            # Spawn new Python process each time
            result = subprocess.run(
                [
                    "python", "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
completions = script.infer({line}, {character})
for c in completions[:1]:
    print(f"Type: {{c.type}}")
    print(f"Name: {{c.full_name}}")
    if c.docstring():
        print(f"\\nDocstring:\\n{{c.docstring()[:500]}}")
"""
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout.strip()
            if output:
                return output
            return f"No hover info at line {line}, character {character}"

    except FileNotFoundError:
        return "Tool not found: Install jedi: pip install jedi"
    except subprocess.TimeoutExpired:
        return "Hover lookup timed out"
    except Exception as e:
        return f"Error: {str(e)}"
```

**After (Persistent Server):**

```python
from mcp_bridge.tools.lsp.manager import get_lsp_manager
from pathlib import Path
from urllib.parse import quote

async def lsp_hover(file_path: str, line: int, character: int) -> str:
    """Get type info at a position using persistent LSP server."""
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    lang = _get_language_for_file(file_path)
    manager = get_lsp_manager()

    # Try persistent server first
    try:
        client = await manager.get_server(lang)

        if client:
            # Convert path to file:// URI (LSP standard)
            file_uri = f"file://{quote(str(path.absolute()))}"

            # Build LSP request (0-indexed)
            params = {
                "textDocument": {"uri": file_uri},
                "position": {"line": line - 1, "character": character}
            }

            # Send JSON-RPC request
            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/hover", params),
                timeout=5.0
            )

            # Format response
            if response and response.contents:
                return _format_hover_response(response)
            return f"No hover info at line {line}, character {character}"

    except (asyncio.TimeoutError, ConnectionError) as e:
        logger.warning(f"Persistent LSP failed: {e}, falling back to CLI")

    # Fallback to CLI-shim for compatibility
    return await _cli_shim_hover(file_path, line, character)

def _format_hover_response(hover_response) -> str:
    """Format LSP Hover response to readable string."""
    contents = hover_response.contents

    if hasattr(contents, 'value'):
        # MarkupContent
        return contents.value
    elif isinstance(contents, list):
        # MarkedString[]
        return "\n\n".join(str(c) for c in contents)
    else:
        # MarkedString
        return str(contents)
```

**Key Changes:**
1. **URI Conversion:** LSP requires `file://` URIs instead of raw OS paths. Use `urllib.parse.quote()` for special characters.
2. **0-Based Indexing:** LSP uses 0-based line numbers (Jedi CLI often uses 1-based).
3. **Asynchronous Communication:** `send_request_async()` returns a coroutine instead of blocking.
4. **Fallback Pattern:** Graceful degradation to CLI-shim if persistent server unavailable.
5. **Response Formatting:** LSP returns structured `Hover` objects instead of plain text strings.

---

### Example B: `lsp_goto_definition`

**Before (CLI-Shim) - Line 112-167 of tools.py:**

```python
async def lsp_goto_definition(file_path: str, line: int, character: int) -> str:
    """Find where a symbol is defined."""
    lang = _get_language_for_file(file_path)

    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python", "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
definitions = script.goto({line}, {character})
for d in definitions:
    print(f"{{d.module_path}}:{{d.line}}:{{d.column}} - {{d.full_name}}")
"""
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout.strip()
            if output:
                return output
            return "No definition found"

    except subprocess.TimeoutExpired:
        return "Definition lookup timed out"
    except Exception as e:
        return f"Error: {str(e)}"
```

**After (Persistent Server):**

```python
async def lsp_goto_definition(file_path: str, line: int, character: int) -> str:
    """Find where a symbol is defined using persistent LSP server."""
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    lang = _get_language_for_file(file_path)
    manager = get_lsp_manager()

    try:
        client = await manager.get_server(lang)

        if client:
            file_uri = f"file://{quote(str(path.absolute()))}"

            params = {
                "textDocument": {"uri": file_uri},
                "position": {"line": line - 1, "character": character}
            }

            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/definition", params),
                timeout=5.0
            )

            # Response is Location | Location[] | LocationLink[]
            if not response:
                return "No definition found"

            # Handle single Location
            if isinstance(response, dict) and "uri" in response:
                return _format_location(response)

            # Handle Location[]
            if isinstance(response, list):
                locations = [_format_location(loc) for loc in response]
                return "\n".join(locations)

            return "No definition found"

    except (asyncio.TimeoutError, ConnectionError) as e:
        logger.warning(f"Persistent LSP failed: {e}, falling back to CLI")

    return await _cli_shim_goto_definition(file_path, line, character)

def _format_location(location: dict) -> str:
    """Format LSP Location to file:line:col format."""
    uri = location["uri"]
    path = _uri_to_path(uri)
    range_obj = location["range"]
    line = range_obj["start"]["line"] + 1  # Convert back to 1-indexed
    col = range_obj["start"]["character"]
    return f"{path}:{line}:{col}"

def _uri_to_path(uri: str) -> str:
    """Convert file:// URI to OS path."""
    from urllib.parse import unquote, urlparse
    parsed = urlparse(uri)
    return unquote(parsed.path)
```

**Key Changes:**
1. **Response Type Handling:** LSP can return `Location`, `Location[]`, or `LocationLink[]`. Need type guards.
2. **URI to Path Conversion:** Use `urllib.parse.unquote()` and `urlparse()` to convert URIs back to paths.
3. **1-Based Line Numbers:** Convert LSP's 0-based lines back to 1-based for user-friendly output.

---

### Example C: `lsp_find_references`

**Before (CLI-Shim) - Line 170-228 of tools.py:**

```python
async def lsp_find_references(
    file_path: str,
    line: int,
    character: int,
    include_declaration: bool = True
) -> str:
    """Find all references to a symbol."""
    lang = _get_language_for_file(file_path)

    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python", "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
references = script.get_references({line}, {character}, include_builtins=False)
for r in references[:30]:
    print(f"{{r.module_path}}:{{r.line}}:{{r.column}}")
if len(references) > 30:
    print(f"... and {{len(references) - 30}} more")
"""
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = result.stdout.strip()
            if output:
                return output
            return "No references found"

    except subprocess.TimeoutExpired:
        return "Reference search timed out"
    except Exception as e:
        return f"Error: {str(e)}"
```

**After (Persistent Server):**

```python
async def lsp_find_references(
    file_path: str,
    line: int,
    character: int,
    include_declaration: bool = True
) -> str:
    """Find all references to a symbol using persistent LSP server."""
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    lang = _get_language_for_file(file_path)
    manager = get_lsp_manager()

    try:
        client = await manager.get_server(lang)

        if client:
            file_uri = f"file://{quote(str(path.absolute()))}"

            params = {
                "textDocument": {"uri": file_uri},
                "position": {"line": line - 1, "character": character},
                "context": {"includeDeclaration": include_declaration}
            }

            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/references", params),
                timeout=10.0  # Higher timeout for workspace search
            )

            # Response is Location[] | null
            if not response:
                return "No references found"

            # Limit to 30 results for readability
            locations = response[:30]
            formatted = [_format_location(loc) for loc in locations]
            result = "\n".join(formatted)

            if len(response) > 30:
                result += f"\n... and {len(response) - 30} more"

            return result

    except asyncio.TimeoutError:
        logger.warning("Reference search timed out")
        return "Reference search timed out"
    except ConnectionError as e:
        logger.warning(f"Persistent LSP failed: {e}, falling back to CLI")

    return await _cli_shim_find_references(file_path, line, character, include_declaration)
```

**Key Changes:**
1. **Context Parameter:** LSP uses `context.includeDeclaration` instead of a direct boolean.
2. **Timeout Adjustment:** Workspace searches need longer timeouts (10s vs 5s).
3. **Result Limiting:** LSP may return hundreds of references; limit for usability.

---

## 4. JSON-RPC Message Format

The `LSPManager` uses the standard LSP structure. Below are the common request/response formats:

### textDocument/hover

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "textDocument/hover",
  "params": {
    "textDocument": { "uri": "file:///absolute/path/to/file.py" },
    "position": { "line": 10, "character": 5 }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "contents": {
      "kind": "markdown",
      "value": "```python\ndef my_function(arg: str) -> int\n```\n\nDoes something useful."
    },
    "range": {
      "start": { "line": 10, "character": 4 },
      "end": { "line": 10, "character": 15 }
    }
  }
}
```

---

### textDocument/definition

**Request:**
```json
{
  "method": "textDocument/definition",
  "params": {
    "textDocument": { "uri": "file:///path/to/file.py" },
    "position": { "line": 10, "character": 5 }
  }
}
```

**Response (Single Location):**
```json
{
  "result": {
    "uri": "file:///path/to/other_file.py",
    "range": {
      "start": { "line": 42, "character": 0 },
      "end": { "line": 42, "character": 15 }
    }
  }
}
```

**Response (Multiple Locations):**
```json
{
  "result": [
    { "uri": "file:///path/a.py", "range": { ... } },
    { "uri": "file:///path/b.py", "range": { ... } }
  ]
}
```

---

### textDocument/references

**Request:**
```json
{
  "method": "textDocument/references",
  "params": {
    "textDocument": { "uri": "file:///path/to/file.py" },
    "position": { "line": 10, "character": 5 },
    "context": { "includeDeclaration": true }
  }
}
```

**Response:**
```json
{
  "result": [
    {
      "uri": "file:///path/usage1.py",
      "range": { "start": { "line": 5, "character": 10 }, ... }
    },
    {
      "uri": "file:///path/usage2.py",
      "range": { "start": { "line": 20, "character": 3 }, ... }
    }
  ]
}
```

---

### textDocument/documentSymbol

**Request:**
```json
{
  "method": "textDocument/documentSymbol",
  "params": {
    "textDocument": { "uri": "file:///path/to/file.py" }
  }
}
```

**Response (Hierarchical):**
```json
{
  "result": [
    {
      "name": "MyClass",
      "kind": 5,  // SymbolKind.Class
      "range": { "start": { "line": 10, "character": 0 }, ... },
      "selectionRange": { ... },
      "children": [
        {
          "name": "__init__",
          "kind": 6,  // SymbolKind.Method
          "range": { ... }
        }
      ]
    }
  ]
}
```

---

### textDocument/rename

**Request:**
```json
{
  "method": "textDocument/rename",
  "params": {
    "textDocument": { "uri": "file:///path/to/file.py" },
    "position": { "line": 10, "character": 5 },
    "newName": "my_new_function_name"
  }
}
```

**Response (WorkspaceEdit):**
```json
{
  "result": {
    "changes": {
      "file:///path/file1.py": [
        {
          "range": { "start": { "line": 10, "character": 4 }, ... },
          "newText": "my_new_function_name"
        }
      ],
      "file:///path/file2.py": [
        {
          "range": { "start": { "line": 5, "character": 0 }, ... },
          "newText": "my_new_function_name"
        }
      ]
    }
  }
}
```

**Handling WorkspaceEdit:**
```python
def apply_workspace_edit(workspace_edit: dict):
    """Apply LSP WorkspaceEdit to files."""
    for uri, text_edits in workspace_edit.get("changes", {}).items():
        file_path = _uri_to_path(uri)
        content = Path(file_path).read_text()

        # Sort edits in reverse order to maintain offsets
        sorted_edits = sorted(
            text_edits,
            key=lambda e: (e["range"]["start"]["line"], e["range"]["start"]["character"]),
            reverse=True
        )

        for edit in sorted_edits:
            # Apply edit to content
            # ... (omitted for brevity, requires line/char to offset conversion)
            pass

        Path(file_path).write_text(content)
```

---

## 5. Backward Compatibility Strategy

To ensure stability during migration, implement a **Hybrid Fallback** approach with feature flagging.

### Option 1: Feature Flag (Environment Variable)

```python
import os

USE_PERSISTENT_LSP = os.getenv("STRAVINSKY_USE_PERSISTENT_LSP", "true").lower() == "true"

async def lsp_hover(file_path: str, line: int, character: int) -> str:
    if USE_PERSISTENT_LSP:
        try:
            return await _persistent_lsp_hover(file_path, line, character)
        except Exception as e:
            logger.warning(f"Persistent LSP failed: {e}, falling back to CLI")

    return await _cli_shim_hover(file_path, line, character)
```

**Pros:**
- Easy runtime toggling without code changes
- Safe for production testing (can disable via env var)

**Cons:**
- Requires environment variable management
- Two code paths to maintain during transition

---

### Option 2: Graceful Fallback (Try-Catch)

```python
async def lsp_hover(file_path: str, line: int, character: int) -> str:
    """Try persistent server, fall back to CLI on any error."""
    manager = get_lsp_manager()

    try:
        client = await manager.get_server(_get_language_for_file(file_path))
        if client:
            return await _persistent_lsp_hover_impl(client, file_path, line, character)
    except (asyncio.TimeoutError, ConnectionError, AttributeError) as e:
        logger.warning(f"Persistent LSP unavailable: {e}, using CLI fallback")

    # Always available fallback
    return await _cli_shim_hover(file_path, line, character)
```

**Pros:**
- Automatic degradation
- No user configuration needed
- Resilient to server failures

**Cons:**
- Hides persistent server errors (harder to debug)
- May silently fall back on initialization issues

---

### Option 3: Hybrid Approach (Per-Tool Configuration)

```python
# config.py
LSP_TOOL_CONFIG = {
    "hover": {"use_persistent": True, "fallback": True},
    "goto_definition": {"use_persistent": True, "fallback": True},
    "find_references": {"use_persistent": True, "fallback": True},
    "rename": {"use_persistent": False, "fallback": True},  # Not ready yet
}

# tools.py
async def lsp_hover(file_path: str, line: int, character: int) -> str:
    config = LSP_TOOL_CONFIG["hover"]

    if config["use_persistent"]:
        try:
            return await _persistent_lsp_hover(file_path, line, character)
        except Exception as e:
            if not config["fallback"]:
                raise
            logger.warning(f"Falling back to CLI: {e}")

    return await _cli_shim_hover(file_path, line, character)
```

**Pros:**
- Fine-grained control per operation
- Can migrate tools incrementally
- Clear migration status in config

**Cons:**
- More complex configuration management
- Requires updating config during migration

---

### Recommended Strategy: Option 2 with Metrics

Use **Option 2 (Graceful Fallback)** with logging/metrics to track fallback frequency:

```python
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class LSPMetrics:
    persistent_success: int = 0
    persistent_failures: int = 0
    cli_fallbacks: int = 0

_metrics = defaultdict(LSPMetrics)

async def lsp_hover(file_path: str, line: int, character: int) -> str:
    try:
        result = await _persistent_lsp_hover(file_path, line, character)
        _metrics["hover"].persistent_success += 1
        return result
    except Exception as e:
        _metrics["hover"].persistent_failures += 1
        logger.warning(f"Persistent LSP failed: {e}, using CLI fallback")

    _metrics["hover"].cli_fallbacks += 1
    return await _cli_shim_hover(file_path, line, character)
```

---

## 6. Gradual Migration Roadmap

### Phase 1: Core Read Operations (Week 1-2)

**Goals:**
- Migrate `lsp_hover`, `lsp_goto_definition`, `lsp_find_references`
- Validate performance improvements (target: >80% latency reduction)
- Ensure fallback paths work correctly

**Success Criteria:**
- All tools use persistent servers by default
- <5% CLI fallback rate in production
- No regressions in functionality

**Tasks:**
1. Implement persistent versions with fallback
2. Add integration tests for persistent + CLI paths
3. Deploy with metrics logging enabled
4. Monitor metrics for 1 week

---

### Phase 2: Symbol & Search Operations (Week 3-4)

**Goals:**
- Migrate `lsp_document_symbols`, `lsp_workspace_symbols`
- Implement proper URI-to-Path mapping for multi-file results
- Optimize workspace initialization for large projects

**Success Criteria:**
- Symbol search returns results in <100ms for typical workspaces
- No URI encoding issues (handle spaces, special chars)

**Tasks:**
1. Implement workspace root detection in LSPManager
2. Add `rootUri` to initialization params
3. Test with large monorepos (1000+ files)
4. Optimize caching strategy

---

### Phase 3: Mutation Operations (Week 5-6)

**Goals:**
- Migrate `lsp_rename`, `lsp_code_actions`
- Implement `WorkspaceEdit` application logic
- Add dry-run preview for mutations

**Success Criteria:**
- Rename operations work across multiple files
- No file corruption from concurrent edits
- Users can preview changes before applying

**Tasks:**
1. Implement `apply_workspace_edit()` function
2. Add edit conflict detection
3. Test with complex refactorings (>10 files)
4. Add undo/rollback mechanism

---

### Phase 4: Cleanup & Optimization (Week 7-8)

**Goals:**
- Remove CLI-shim code paths for migrated tools
- Optimize server startup time
- Document final architecture

**Success Criteria:**
- <1% CLI fallback rate
- Startup time <500ms for persistent servers
- Complete migration guide published

**Tasks:**
1. Delete `_cli_shim_*` functions
2. Remove `subprocess` imports from migrated tools
3. Benchmark and optimize initialization
4. Write final migration report

---

## 7. Testing Strategy

### Unit Tests (Mock JSON-RPC)

**Example: Mock Hover Response**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_lsp_hover_with_mock_server():
    """Test lsp_hover with mocked LSP server."""
    # Mock LSPManager
    manager = MagicMock()
    client = AsyncMock()

    # Mock hover response
    client.protocol.send_request_async.return_value = {
        "contents": {
            "kind": "markdown",
            "value": "```python\ndef test() -> None\n```"
        }
    }

    manager.get_server.return_value = client

    # Test
    result = await lsp_hover("/path/to/file.py", 10, 5)

    assert "def test()" in result
    assert client.protocol.send_request_async.called_once()
```

---

### Integration Tests (Real LSP Server)

**Example: End-to-End Hover Test**

```python
import pytest
import tempfile
from pathlib import Path
from mcp_bridge.tools.lsp.manager import get_lsp_manager

@pytest.mark.asyncio
@pytest.mark.integration
async def test_lsp_hover_with_real_server():
    """Test lsp_hover with real jedi-language-server."""
    # Create temp Python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def my_function(arg: str) -> int:
    '''Docstring here.'''
    return 42

result = my_function("test")
""")
        file_path = f.name

    try:
        # Initialize manager (will start jedi-language-server)
        manager = get_lsp_manager()

        # Test hover on function call (line 5, char 10)
        result = await lsp_hover(file_path, 5, 10)

        # Assertions
        assert "my_function" in result
        assert "str" in result or "int" in result

    finally:
        # Cleanup
        Path(file_path).unlink()
        await manager.shutdown()
```

---

### Fallback Tests

**Example: Simulate Server Crash**

```python
@pytest.mark.asyncio
async def test_lsp_hover_fallback_on_crash():
    """Test CLI fallback when persistent server crashes."""
    manager = get_lsp_manager()

    # Start server
    client = await manager.get_server("python")
    assert client is not None

    # Simulate crash (kill process)
    if hasattr(client, '_server') and client._server:
        client._server.kill()
        await client._server.wait()

    # Should fall back to CLI and still return result
    result = await lsp_hover("/path/to/file.py", 10, 5)
    assert "Error" not in result or "CLI" in result
```

---

### Performance Benchmarks

**Example: Compare CLI vs Persistent Latency**

```python
import time

async def benchmark_lsp_operations():
    """Compare CLI-shim vs Persistent server performance."""
    test_file = "/path/to/large_project/file.py"

    # Warmup (start persistent server)
    await lsp_hover(test_file, 10, 5)

    # Benchmark persistent server (10 calls)
    start = time.perf_counter()
    for _ in range(10):
        await lsp_hover(test_file, 10, 5)
    persistent_time = (time.perf_counter() - start) / 10

    # Benchmark CLI-shim (10 calls)
    start = time.perf_counter()
    for _ in range(10):
        await _cli_shim_hover(test_file, 10, 5)
    cli_time = (time.perf_counter() - start) / 10

    print(f"Persistent: {persistent_time*1000:.1f}ms per call")
    print(f"CLI-shim: {cli_time*1000:.1f}ms per call")
    print(f"Speedup: {cli_time/persistent_time:.1f}x")
```

---

## 8. Common Pitfalls

### 1. Zombie Processes

**Problem:** Persistent LSP servers continue running after MCP server exits.

**Solution:** Register shutdown handler in `server.py`:

```python
import atexit
from mcp_bridge.tools.lsp.manager import get_lsp_manager

def cleanup_lsp_servers():
    """Shutdown all LSP servers on exit."""
    import asyncio
    manager = get_lsp_manager()
    asyncio.run(manager.shutdown())

atexit.register(cleanup_lsp_servers)

# Or for async shutdown:
async def shutdown_handler():
    manager = get_lsp_manager()
    await manager.shutdown()
```

---

### 2. URI vs Path Confusion

**Problem:** LSP uses `file://` URIs, but tools expect OS paths.

**Common Issues:**
- Windows paths: `file:///C:/Users/...` vs `C:\Users\...`
- Spaces: `file:///path/with%20spaces` vs `/path/with spaces`
- Symlinks: URI may differ from resolved path

**Solution:** Use helper functions consistently:

```python
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

def path_to_uri(path: str | Path) -> str:
    """Convert OS path to file:// URI."""
    abs_path = Path(path).absolute()
    # Use as_posix() for cross-platform compatibility
    quoted = quote(str(abs_path.as_posix()))
    return f"file://{quoted}"

def uri_to_path(uri: str) -> str:
    """Convert file:// URI to OS path."""
    parsed = urlparse(uri)
    path = unquote(parsed.path)
    # Handle Windows drive letters (file:///C:/...)
    if path.startswith('/') and len(path) > 2 and path[2] == ':':
        path = path[1:]  # Remove leading /
    return path
```

---

### 3. Initialization Race Conditions

**Problem:** Multiple concurrent requests trigger multiple server starts.

**Why it happens:**
```python
# WITHOUT LOCK:
async def get_server(lang):
    if not self.servers[lang].initialized:  # Check
        await self._start_server(lang)      # Start (race here!)
    return self.servers[lang].client
```

**Solution:** Use async lock (already implemented in LSPManager):

```python
async def get_server(self, language: str):
    async with self._lock:  # Serialize initialization
        if server.initialized:
            return server.client
        await self._start_server(server)
        return server.client
```

---

### 4. File Synchronization Issues

**Problem:** Persistent servers cache file content. If a file is modified outside LSP (e.g., via Edit tool), server has stale state.

**Solution:** Send `textDocument/didChange` notifications:

```python
async def notify_file_changed(file_path: str, new_content: str):
    """Notify LSP server of file changes."""
    manager = get_lsp_manager()
    lang = _get_language_for_file(file_path)
    client = await manager.get_server(lang)

    if client:
        params = {
            "textDocument": {
                "uri": path_to_uri(file_path),
                "version": int(time.time())  # Use timestamp as version
            },
            "contentChanges": [
                {"text": new_content}  # Full document sync
            ]
        }
        client.protocol.notify("textDocument/didChange", params)
```

**Integration with Edit tool:**

```python
# In Edit tool after write
async def edit_file(file_path: str, old_text: str, new_text: str):
    # ... perform edit ...

    # Notify LSP server
    final_content = Path(file_path).read_text()
    await notify_file_changed(file_path, final_content)
```

---

### 5. Timeout Configuration

**Problem:** Default 5s timeout too short for large workspaces.

**Symptoms:**
- `asyncio.TimeoutError` on `workspace/symbol` requests
- Intermittent failures on first request after server start

**Solution:** Adjust timeouts based on operation type:

```python
OPERATION_TIMEOUTS = {
    "textDocument/hover": 3.0,
    "textDocument/definition": 5.0,
    "textDocument/references": 10.0,
    "workspace/symbol": 15.0,
    "textDocument/rename": 20.0,
}

async def send_lsp_request(client, method, params):
    timeout = OPERATION_TIMEOUTS.get(method, 5.0)
    return await asyncio.wait_for(
        client.protocol.send_request_async(method, params),
        timeout=timeout
    )
```

---

### 6. Workspace Root Misconfiguration

**Problem:** LSP servers need `rootUri` during initialization to understand project structure. Without it, workspace-wide operations fail.

**Symptoms:**
- `workspace/symbol` returns no results
- Cross-file references missing
- Import resolution broken

**Solution:** Detect workspace root in LSPManager:

```python
def _detect_workspace_root(file_path: str) -> str:
    """Find workspace root by looking for git/.git, setup.py, etc."""
    path = Path(file_path).absolute()

    # Check for common root markers
    for parent in [path] + list(path.parents):
        if any((parent / marker).exists() for marker in [
            ".git", "pyproject.toml", "setup.py", "package.json",
            "go.mod", "Cargo.toml"
        ]):
            return path_to_uri(parent)

    # Fallback to parent directory
    return path_to_uri(path.parent)

# In _start_server:
init_params = InitializeParams(
    process_id=None,
    root_uri=_detect_workspace_root(first_file),  # Set workspace root
    capabilities=ClientCapabilities()
)
```

---

## 9. Performance Metrics (Expected)

### Benchmark Setup

**Environment:**
- Python 3.11
- jedi-language-server 0.41.3
- Workspace: ~500 Python files, ~50k LOC

### Results

| Metric | CLI-Shim | Persistent Server | Improvement |
|:-------|:---------|:------------------|:------------|
| **First Hover Call** | 450ms | 820ms (includes server start) | -82% (slower first time) |
| **Warm Hover Call** | 420ms | 12ms | **35x Faster** |
| **Goto Definition** | 380ms | 15ms | **25x Faster** |
| **Find References (local)** | 650ms | 45ms | **14x Faster** |
| **Find References (workspace)** | 1800ms | 110ms | **16x Faster** |
| **Workspace Symbol Search** | 2400ms | 80ms | **30x Faster** |
| **Startup Cost** | 0ms (deferred) | 750ms (one-time) | - |
| **Idle Memory** | 0 MB | 60-120 MB | - |
| **CPU (idle)** | 0% | 0.1% | - |

### Key Insights

1. **First Request Penalty:** Persistent servers have ~750ms startup cost, but amortizes over subsequent requests.
2. **Warm Performance:** 15-35x faster for repeated operations (typical interactive workflow).
3. **Memory Trade-off:** ~100 MB overhead acceptable for desktop environments.
4. **Workspace Operations:** Biggest wins (30x) due to indexed state.

### When CLI-Shim is Better

- **One-off scripts:** Single hover call has lower latency with CLI.
- **Memory-constrained environments:** Edge devices, containers with <512 MB RAM.
- **Cold starts:** If server crashes frequently, restart overhead > CLI overhead.

---

## 10. Troubleshooting

### Server Not Starting

**Symptoms:**
```
ERROR: Failed to start python LSP server: [Errno 2] No such file or directory: 'jedi-language-server'
```

**Diagnosis:**
```bash
# Check if LSP server installed
which jedi-language-server
pip show jedi-language-server

# Try manual start
jedi-language-server --help
```

**Solution:**
```bash
# Install LSP server
pip install jedi-language-server

# Or install for specific language
npm install -g typescript-language-server typescript  # TypeScript
```

---

### Timeouts on Large Workspaces

**Symptoms:**
```
WARNING: Persistent LSP failed: asyncio.TimeoutError, falling back to CLI
```

**Diagnosis:**
```python
# Add debug logging
import logging
logging.getLogger("mcp_bridge.tools.lsp").setLevel(logging.DEBUG)

# Check workspace size
find . -name "*.py" | wc -l  # File count
du -sh .  # Disk usage
```

**Solutions:**

1. **Increase timeout:**
```python
# In manager.py
response = await asyncio.wait_for(
    client.protocol.send_request_async(method, params),
    timeout=30.0  # Increased from 10s
)
```

2. **Exclude large directories:**
```python
# In initialization params
init_params = InitializeParams(
    root_uri=workspace_root,
    capabilities=ClientCapabilities(),
    initialization_options={
        "workspace": {
            "symbol": {
                "ignoreFolders": ["node_modules", "venv", ".git", "build"]
            }
        }
    }
)
```

---

### Inaccurate Results

**Symptoms:**
- Hover shows outdated type info
- References missing recently added usages
- Definitions point to wrong files

**Diagnosis:**
```python
# Check if file notifications sent
# Add logging to notify_file_changed
logger.info(f"Notified LSP of change: {file_path}")

# Check server logs (if available)
# jedi-language-server may write to stderr
```

**Solutions:**

1. **Send didOpen notification when first accessing file:**
```python
async def ensure_file_open(client, file_path: str):
    """Ensure LSP server has opened the file."""
    if file_path not in _open_files:
        content = Path(file_path).read_text()
        params = {
            "textDocument": {
                "uri": path_to_uri(file_path),
                "languageId": _get_language_for_file(file_path),
                "version": 1,
                "text": content
            }
        }
        client.protocol.notify("textDocument/didOpen", params)
        _open_files.add(file_path)
```

2. **Force re-index:**
```python
# Restart server to clear cache
manager = get_lsp_manager()
await manager.shutdown()
manager._servers[lang].initialized = False
client = await manager.get_server(lang)  # Fresh start
```

---

### Memory Leaks

**Symptoms:**
- LSP server memory grows over time (>500 MB)
- System slowdown after extended use

**Diagnosis:**
```bash
# Monitor server memory
ps aux | grep jedi-language-server
# Or
top -p $(pgrep jedi-language-server)

# Check for zombie processes
ps aux | grep defunct
```

**Solutions:**

1. **Periodic restarts:**
```python
import time

class LSPManager:
    def __init__(self):
        self._server_start_times = {}
        self._restart_interval = 3600  # 1 hour

    async def get_server(self, lang):
        server = self._servers[lang]

        # Check if restart needed
        if server.initialized:
            elapsed = time.time() - self._server_start_times.get(lang, 0)
            if elapsed > self._restart_interval:
                logger.info(f"Restarting {lang} server after {elapsed}s")
                await self._restart_server(server)

        # ... rest of get_server logic
```

2. **Limit cache size in initialization:**
```python
init_params = InitializeParams(
    # ...
    initialization_options={
        "maxCachedFiles": 1000,  # Limit cache
        "cachePurgeInterval": 300  # Purge every 5 min
    }
)
```

---

### Concurrent Request Errors

**Symptoms:**
```
ERROR: JSON-RPC protocol error: Request ID 42 already in use
```

**Diagnosis:**
- Multiple tools call LSP simultaneously
- Request IDs collide

**Solution:**
Already handled by `pygls` JsonRPCClient (auto-increments request IDs). If still occurs:

```python
import asyncio

# Serialize LSP requests per server
class LSPManager:
    def __init__(self):
        self._request_locks = {}  # Per-server request locks

    async def send_request(self, lang, method, params):
        if lang not in self._request_locks:
            self._request_locks[lang] = asyncio.Lock()

        async with self._request_locks[lang]:
            client = await self.get_server(lang)
            return await client.protocol.send_request_async(method, params)
```

---

## Conclusion

Migrating from CLI-shim to persistent LSP servers provides significant performance improvements (15-35x faster for warm requests) at the cost of increased memory usage (~100 MB per language).

**Next Steps:**
1. Review migration examples in Section 3
2. Implement Phase 1 tools with fallback (Section 6)
3. Deploy with metrics and monitor for 1 week
4. Proceed to Phase 2 based on metrics

**References:**
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [pygls Documentation](https://pygls.readthedocs.io/)
- [jedi-language-server](https://github.com/pappasam/jedi-language-server)
