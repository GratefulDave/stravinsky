# Stravinsky LSP & Orchestration Enhancement Plan

> **Generated**: 2026-01-06 | **Status**: Ready for Implementation

## Executive Summary

This plan covers three major enhancements to Stravinsky:

1. **LSP Refactoring Tools** - Add `lsp_code_action_resolve` and `lsp_extract_refactor`
2. **Persistent LSP Servers** - Replace CLI-shim pattern with true LSP client-server
3. **Hierarchical Orchestration** - Add sub-orchestrators (Research Lead, Implementation Lead)

---

## Part 1: LSP Refactoring Tools

### 1.1 Current State

| Tool | Status | Languages |
|------|--------|-----------|
| `lsp_hover` | ✅ Exists | Python (jedi) |
| `lsp_goto_definition` | ✅ Exists | Python (jedi) |
| `lsp_find_references` | ✅ Exists | Python (jedi) |
| `lsp_document_symbols` | ✅ Exists | Python (jedi/ctags) |
| `lsp_workspace_symbols` | ✅ Exists | All (ripgrep+ctags) |
| `lsp_diagnostics` | ✅ Exists | Python (ruff), TS (tsc) |
| `lsp_servers` | ✅ Exists | Metadata |
| `lsp_prepare_rename` | ✅ Exists | Python (jedi) |
| `lsp_rename` | ✅ Exists | Python (jedi) |
| `lsp_code_actions` | ✅ Exists | Python (ruff) |
| `lsp_code_action_resolve` | ❌ Missing | - |
| `lsp_extract_refactor` | ❌ Missing | - |

### 1.2 New Tool: `lsp_code_action_resolve`

**Purpose**: Apply a specific code action/fix returned by `lsp_code_actions`

**Signature**:
```python
async def lsp_code_action_resolve(
    file_path: str,
    action_code: str,  # e.g., "F401", "E501"
    line: int = None   # Optional line filter
) -> str
```

**Implementation**:
```python
# mcp_bridge/tools/lsp/tools.py

async def lsp_code_action_resolve(
    file_path: str,
    action_code: str,
    line: int = None
) -> str:
    """Apply a specific code action/fix to a file."""
    import sys
    print(f"🔧 LSP-RESOLVE: {action_code} at {file_path}", file=sys.stderr)

    path = Path(file_path)
    if not path.exists():
        return f"Error: File {file_path} not found."

    lang = _get_language_for_file(file_path)

    if lang == "python":
        try:
            result = subprocess.run(
                ["ruff", "check", str(path), "--fix", "--select", action_code],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                return f"✅ Applied fix [{action_code}] to {path.name}"
            else:
                return f"⚠️ {result.stderr.strip() or 'No changes needed'}"

        except FileNotFoundError:
            return "Install ruff: pip install ruff"
        except subprocess.TimeoutExpired:
            return "Timeout applying fix"

    return f"Code action resolve not implemented for {lang}"
```

**Registration** (server_tools.py):
```python
Tool(
    name="lsp_code_action_resolve",
    description="Apply a specific code action/fix to a file (e.g., fix F401 unused import)",
    inputSchema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute path to file"},
            "action_code": {"type": "string", "description": "Code action ID (e.g., F401, E501)"},
            "line": {"type": "integer", "description": "Optional line number filter"},
        },
        "required": ["file_path", "action_code"],
    },
),
```

### 1.3 New Tool: `lsp_extract_refactor`

**Purpose**: Extract method or variable from selected code range

**Signature**:
```python
async def lsp_extract_refactor(
    file_path: str,
    start_line: int,
    start_char: int,
    end_line: int,
    end_char: int,
    new_name: str,
    kind: str = "function"  # "function" or "variable"
) -> str
```

**Implementation** (using jedi for Python):
```python
async def lsp_extract_refactor(
    file_path: str,
    start_line: int,
    start_char: int,
    end_line: int,
    end_char: int,
    new_name: str,
    kind: str = "function"
) -> str:
    """Extract code to function or variable."""
    import sys
    print(f"🔧 LSP-EXTRACT: {kind} '{new_name}' from {file_path}:{start_line}-{end_line}", file=sys.stderr)

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    lang = _get_language_for_file(file_path)

    if lang == "python":
        try:
            import jedi
            source = path.read_text()
            script = jedi.Script(source, path=path)

            if kind == "function":
                refactoring = script.extract_function(
                    line=start_line,
                    until_line=end_line,
                    new_name=new_name
                )
            else:  # variable
                refactoring = script.extract_variable(
                    line=start_line,
                    until_line=end_line,
                    new_name=new_name
                )

            # Get the diff
            changes = refactoring.get_diff()
            return f"✅ Extract {kind} preview:\n```diff\n{changes}\n```\n\nApply with dry_run=False"

        except AttributeError:
            return "Jedi version doesn't support extract refactoring. Upgrade: pip install -U jedi"
        except Exception as e:
            return f"Extract failed: {str(e)}"

    return f"Extract refactoring not implemented for {lang}"
```

---

## Part 2: Persistent LSP Servers

### 2.1 Current Architecture (CLI-Shim)

```
Tool call → subprocess.run(["jedi", ...]) → parse stdout → return → process dies
```

**Problems**:
- Cold start on every call
- No workspace indexing cache
- No incremental analysis
- Can't use full LSP protocol features

### 2.2 Target Architecture (Persistent)

```
MCP Server Start
       ↓
   LSPManager.init()
       ↓
   ┌─────────────────────────────────┐
   │  LSP Server Pool (Lazy Start)   │
   │  ┌─────────┐  ┌──────────────┐  │
   │  │  jedi   │  │  tsserver    │  │
   │  │ (Python)│  │ (TypeScript) │  │
   │  └────┬────┘  └──────┬───────┘  │
   │       │              │          │
   │       └──────┬───────┘          │
   │              ↓                  │
   │     JSON-RPC over stdio         │
   └─────────────────────────────────┘
              ↓
    Tool calls route to appropriate server
              ↓
    Servers stay alive until MCP shutdown
```

### 2.3 Implementation: LSPManager

**New file**: `mcp_bridge/tools/lsp/manager.py`

```python
"""Persistent LSP Server Manager"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class LSPServer:
    name: str
    command: list[str]
    languages: list[str]
    process: Optional[asyncio.subprocess.Process] = None
    initialized: bool = False

class LSPManager:
    """Manages persistent LSP server connections."""

    _instance: Optional['LSPManager'] = None

    def __init__(self):
        self.servers: Dict[str, LSPServer] = {
            "jedi": LSPServer(
                name="jedi-language-server",
                command=["jedi-language-server"],
                languages=["python"]
            ),
            "typescript": LSPServer(
                name="typescript-language-server",
                command=["typescript-language-server", "--stdio"],
                languages=["typescript", "javascript", "typescriptreact", "javascriptreact"]
            ),
        }
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> 'LSPManager':
        if cls._instance is None:
            cls._instance = LSPManager()
        return cls._instance

    async def get_server(self, language: str) -> Optional[LSPServer]:
        """Get or start the LSP server for a language."""
        for server in self.servers.values():
            if language in server.languages:
                async with self._lock:
                    if server.process is None:
                        await self._start_server(server)
                return server
        return None

    async def _start_server(self, server: LSPServer):
        """Start an LSP server process."""
        import sys
        print(f"🚀 Starting LSP: {server.name}", file=sys.stderr)

        server.process = await asyncio.create_subprocess_exec(
            *server.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Send initialize request
        await self._initialize(server)
        server.initialized = True

    async def _initialize(self, server: LSPServer):
        """Send LSP initialize handshake."""
        init_params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": f"file://{Path.cwd()}",
                "capabilities": {
                    "textDocument": {
                        "codeAction": {"codeActionLiteralSupport": {}},
                        "rename": {"prepareSupport": True},
                    }
                }
            }
        }
        await self._send_request(server, init_params)

        # Send initialized notification
        await self._send_notification(server, {"jsonrpc": "2.0", "method": "initialized", "params": {}})

    async def _send_request(self, server: LSPServer, request: dict) -> dict:
        """Send JSON-RPC request and wait for response."""
        content = json.dumps(request)
        message = f"Content-Length: {len(content)}\r\n\r\n{content}"

        server.process.stdin.write(message.encode())
        await server.process.stdin.drain()

        # Read response
        return await self._read_response(server)

    async def _send_notification(self, server: LSPServer, notification: dict):
        """Send JSON-RPC notification (no response expected)."""
        content = json.dumps(notification)
        message = f"Content-Length: {len(content)}\r\n\r\n{content}"

        server.process.stdin.write(message.encode())
        await server.process.stdin.drain()

    async def _read_response(self, server: LSPServer) -> dict:
        """Read JSON-RPC response from server."""
        # Read headers
        headers = {}
        while True:
            line = await server.process.stdout.readline()
            line = line.decode().strip()
            if not line:
                break
            key, value = line.split(": ", 1)
            headers[key] = value

        # Read content
        content_length = int(headers.get("Content-Length", 0))
        content = await server.process.stdout.read(content_length)
        return json.loads(content)

    async def shutdown(self):
        """Shutdown all LSP servers gracefully."""
        for server in self.servers.values():
            if server.process:
                await self._send_request(server, {
                    "jsonrpc": "2.0",
                    "id": 999,
                    "method": "shutdown",
                    "params": None
                })
                await self._send_notification(server, {
                    "jsonrpc": "2.0",
                    "method": "exit",
                    "params": None
                })
                server.process.terminate()
                server.process = None
```

### 2.4 Migration Path

**Phase 1**: Add LSPManager alongside existing CLI tools
**Phase 2**: Route Python tools through persistent jedi-language-server
**Phase 3**: Add TypeScript support via typescript-language-server
**Phase 4**: Deprecate CLI-shim functions

---

## Part 3: Hierarchical Orchestration

### 3.1 Current Architecture (Flat)

```
Stravinsky (Claude Sonnet) ─┬─ explore (Gemini)
                            ├─ dewey (Gemini)
                            ├─ frontend (Gemini Pro)
                            ├─ debugger (Claude)
                            └─ delphi (GPT-5.2)
```

**Problems**:
- Stravinsky holds ALL context for ALL agents
- Expensive Claude tokens for coordination logic
- No domain-specific synthesis

### 3.2 Target Architecture (Hierarchical)

```
┌─────────────────────────────────────────────────────────────┐
│              Stravinsky (Meta-Orchestrator)                 │
│             Claude Sonnet - Strategic Decisions             │
└───────────────┬─────────────────────┬───────────────────────┘
                │                     │
                ▼                     ▼
┌───────────────────────┐  ┌───────────────────────────────┐
│    Research Lead      │  │    Implementation Lead        │
│   (Gemini Flash)      │  │    (Claude Haiku)             │
│                       │  │                               │
│   Coordinates:        │  │   Coordinates:                │
│   - explore agents    │  │   - frontend agent            │
│   - dewey agents      │  │   - debugger agent            │
│   - grep-app searches │  │   - code-reviewer agent       │
└───────────┬───────────┘  └───────────────┬───────────────┘
            │                              │
     ┌──────┴──────┐                ┌──────┴──────┐
     ▼             ▼                ▼             ▼
  explore       dewey          frontend      debugger
 (Gemini)     (Gemini)       (Gemini Pro)   (Claude)
```

### 3.3 New Agent: Research Lead

**File**: `.claude/agents/research-lead.md`

```markdown
---
name: research-lead
description: |
  Coordinates research agents (explore, dewey) to gather comprehensive information.
  Returns synthesized findings, not raw agent outputs.
tools: Read, Grep, Glob, mcp__stravinsky__agent_spawn, mcp__stravinsky__agent_output, mcp__stravinsky__invoke_gemini
model: haiku
---

# Research Lead

You coordinate research tasks by spawning explore and dewey agents in parallel.

## Your Role

1. Receive research objective from Stravinsky
2. Decompose into parallel search tasks
3. Spawn explore/dewey agents for each task
4. Collect and SYNTHESIZE results
5. Return structured findings (not raw outputs)

## Output Format

Always return a Research Brief:

```json
{
  "objective": "Original research goal",
  "findings": [
    {"source": "agent_id", "summary": "Key finding", "confidence": "high/medium/low"},
    ...
  ],
  "synthesis": "Combined analysis of all findings",
  "gaps": ["Information we couldn't find"],
  "recommendations": ["Suggested next steps"]
}
```

## Model Routing

Use `invoke_gemini` with `model="gemini-3-flash"` for ALL synthesis work.
You are a CHEAP agent - do NOT call expensive models.
```

### 3.4 New Agent: Implementation Lead

**File**: `.claude/agents/implementation-lead.md`

```markdown
---
name: implementation-lead
description: |
  Coordinates implementation agents (frontend, debugger, code-reviewer).
  Receives research brief, produces working code.
tools: Read, Write, Edit, Grep, Glob, mcp__stravinsky__agent_spawn, mcp__stravinsky__agent_output, mcp__stravinsky__lsp_diagnostics
model: haiku
---

# Implementation Lead

You coordinate implementation based on research findings.

## Your Role

1. Receive Research Brief from Stravinsky
2. Create implementation plan
3. Delegate to specialists:
   - frontend: UI/visual work
   - debugger: Fix failures
   - code-reviewer: Quality checks
4. Verify with lsp_diagnostics
5. Return Implementation Report

## Output Format

```json
{
  "objective": "What was implemented",
  "files_changed": ["path/to/file.py"],
  "tests_status": "pass/fail/skipped",
  "diagnostics": "clean/warnings/errors",
  "blockers": ["Issues preventing completion"]
}
```

## Escalation Rules

- After 2 failed attempts → spawn debugger
- After debugger fails → escalate to Stravinsky with context
- NEVER call delphi directly (that's Stravinsky's decision)
```

### 3.5 Agent Manager Updates

**File**: `mcp_bridge/tools/agent_manager.py` (additions)

```python
# Add to AGENT_MODEL_ROUTING
AGENT_MODEL_ROUTING = {
    # ... existing ...
    "research-lead": None,  # Uses invoke_gemini internally
    "implementation-lead": None,  # Uses invoke_gemini internally
}

# Add to AGENT_COST_TIERS
AGENT_COST_TIERS = {
    # ... existing ...
    "research-lead": "CHEAP",
    "implementation-lead": "CHEAP",
}

# Add to AGENT_DISPLAY_MODELS
AGENT_DISPLAY_MODELS = {
    # ... existing ...
    "research-lead": "gemini-3-flash",
    "implementation-lead": "haiku",
}
```

### 3.6 Handoff Protocol

**Research → Implementation Handoff**:

```python
# Stravinsky spawns Research Lead
research_task = agent_spawn(
    agent_type="research-lead",
    prompt="""
    OBJECTIVE: Understand how to add TypeScript LSP support

    SPAWN THESE AGENTS IN PARALLEL:
    1. explore: Find current LSP implementation in mcp_bridge/tools/lsp/
    2. explore: Find agent_manager.py patterns
    3. dewey: Research typescript-language-server integration

    RETURN: Research Brief JSON
    """,
    description="Research TS LSP"
)

# Wait for research
research_brief = agent_output(research_task, block=True)

# Stravinsky spawns Implementation Lead with research
impl_task = agent_spawn(
    agent_type="implementation-lead",
    prompt=f"""
    RESEARCH BRIEF: {research_brief}

    OBJECTIVE: Implement TypeScript LSP support based on findings

    DELEGATE AS NEEDED:
    - frontend: If UI changes needed
    - code-reviewer: Before marking complete

    RETURN: Implementation Report JSON
    """,
    description="Implement TS LSP"
)
```

---

## Implementation Checklist

### Phase 1: LSP Tools (Week 1)

- [ ] Add `lsp_code_action_resolve` to `tools.py`
- [ ] Add `lsp_extract_refactor` to `tools.py`
- [ ] Register both in `server_tools.py`
- [ ] Add handlers in `server.py`
- [ ] Update `__init__.py` exports
- [ ] Test with Python files

### Phase 2: Persistent LSP (Week 2)

- [ ] Create `mcp_bridge/tools/lsp/manager.py`
- [ ] Add jedi-language-server support
- [ ] Add typescript-language-server support
- [ ] Update existing tools to use manager
- [ ] Add graceful shutdown to MCP server
- [ ] Test multi-language support

### Phase 3: Hierarchical Orchestration (Week 3)

- [ ] Create `.claude/agents/research-lead.md`
- [ ] Create `.claude/agents/implementation-lead.md`
- [ ] Update `agent_manager.py` with new agent types
- [ ] Update Stravinsky prompt for hierarchical delegation
- [ ] Test end-to-end workflow
- [ ] Document handoff protocol

### Phase 4: Documentation (Week 4)

- [ ] Update README.md with new tools
- [ ] Update tool count (31 → 33)
- [ ] Add hierarchical orchestration guide
- [ ] Update CLAUDE.md with new patterns

---

## Dependencies

### Required Packages

```bash
# LSP servers
pip install jedi-language-server
npm install -g typescript typescript-language-server

# Python dependencies (already in project)
pip install jedi ruff
```

### System Requirements

- Node.js 18+ (for typescript-language-server)
- Python 3.10+ (for async subprocess)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LSP server crashes | Medium | High | Auto-restart with backoff |
| Hierarchical loops | Low | High | Max recursion depth (3) |
| Context loss in handoffs | Medium | Medium | JSON schema validation |
| Increased memory | High | Low | Lazy server startup |

---

## Success Metrics

1. **LSP Tools**: `lsp_code_action_resolve` successfully applies ruff fixes
2. **Persistent LSP**: 10x faster hover/definition on repeated calls
3. **Hierarchical**: Complex tasks use 30% fewer Stravinsky tokens

---

## Next Steps

1. Review this plan
2. Approve phases or request changes
3. Begin Phase 1 implementation

*Plan generated by Stravinsky Orchestrator with ULTRATHINK*
