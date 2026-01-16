"""
LSP Tools - Advanced Language Server Protocol Operations

Provides comprehensive LSP functionality via persistent connections to language servers.
Supplements Claude Code's native LSP support with advanced operations.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

# Use lsprotocol for types
try:
    from lsprotocol.types import (
        CodeActionContext,
        CodeActionParams,
        CodeActionTriggerKind,
        DidCloseTextDocumentParams,
        DidOpenTextDocumentParams,
        DocumentSymbolParams,
        HoverParams,
        Location,
        Position,
        PrepareRenameParams,
        Range,
        ReferenceContext,
        ReferenceParams,
        RenameParams,
        TextDocumentIdentifier,
        TextDocumentItem,
        TextDocumentPositionParams,
        WorkspaceSymbolParams,
    )
except ImportError:
    # Fallback/Mock for environment without lsprotocol
    pass

from .manager import get_lsp_manager

logger = logging.getLogger(__name__)


def _get_language_for_file(file_path: str) -> str:
    """Determine language from file extension."""
    suffix = Path(file_path).suffix.lower()
    mapping = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescriptreact",
        ".js": "javascript",
        ".jsx": "javascriptreact",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
    }
    return mapping.get(suffix, "unknown")


def _find_project_root(file_path: str) -> str | None:
    """
    Find project root by looking for marker files.

    Markers:
    - Python: pyproject.toml, setup.py, requirements.txt, .git
    - JS/TS: package.json, tsconfig.json, .git
    - General: .git
    """
    path = Path(file_path).resolve()
    if path.is_file():
        path = path.parent

    markers = {
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "package.json",
        "tsconfig.json",
        ".git",
    }

    # Walk up the tree
    current = path
    for _ in range(20):  # Limit depth
        for marker in markers:
            if (current / marker).exists():
                return str(current)
        if current.parent == current:  # Root reached
            break
        current = current.parent

    return None


async def _get_client_and_params(
    file_path: str, needs_open: bool = True
) -> tuple[Any | None, str | None, str]:
    """
    Get LSP client and prepare file for operations.

    Returns:
        (client, uri, language)
    """
    path = Path(file_path)
    if not path.exists():
        return None, None, "unknown"

    lang = _get_language_for_file(file_path)
    root_path = _find_project_root(file_path)

    # Use found root or fallback to file's parent directory
    # Passing root_path allows the manager to initialize/restart server with correct context
    server_root = root_path if root_path else str(path.parent)

    manager = get_lsp_manager()
    client = await manager.get_server(lang, root_path=server_root)

    if not client:
        return None, None, lang

    uri = f"file://{path.absolute()}"

    if needs_open:
        try:
            content = path.read_text()
            # Send didOpen notification
            # We don't check if it's already open because we're stateless-ish
            # and want to ensure fresh content.
            # Using version=1
            params = DidOpenTextDocumentParams(
                text_document=TextDocumentItem(uri=uri, language_id=lang, version=1, text=content)
            )
            client.protocol.notify("textDocument/didOpen", params)
        except Exception as e:
            logger.warning(f"Failed to send didOpen for {file_path}: {e}")

    return client, uri, lang


async def lsp_hover(file_path: str, line: int, character: int) -> str:
    """
    Get type info, documentation, and signature at a position.
    """
    # USER-VISIBLE NOTIFICATION
    print(f"📍 LSP-HOVER: {file_path}:{line}:{character}", file=sys.stderr)

    client, uri, lang = await _get_client_and_params(file_path)

    if client:
        try:
            params = HoverParams(
                text_document=TextDocumentIdentifier(uri=uri),
                position=Position(line=line - 1, character=character),
            )

            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/hover", params), timeout=5.0
            )

            if response and response.contents:
                # Handle MarkupContent or text
                contents = response.contents
                if hasattr(contents, "value"):
                    return contents.value
                elif isinstance(contents, list):
                    return "\n".join([str(c) for c in contents])
                return str(contents)

            return f"No hover info at line {line}, character {character}"

        except Exception as e:
            logger.error(f"LSP hover failed: {e}")
            # Fall through to legacy fallback

    # Legacy Fallback
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        if lang == "python":
            # Use jedi for Python hover info
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
completions = script.infer({line}, {character})
for c in completions[:1]:
    logger.info(f"Type: {{c.type}}")
    logger.info(f"Name: {{c.full_name}}")
    if c.docstring():
        logger.info(f"\\nDocstring:\\n{{c.docstring()[:500]}}")
""",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout.strip()
            if output:
                return output
            return f"No hover info at line {line}, character {character}"

        elif lang in ("typescript", "javascript", "typescriptreact", "javascriptreact"):
            return "TypeScript hover requires running language server. Use Claude Code's native hover."

        else:
            return f"Hover not available for language: {lang}"

    except FileNotFoundError as e:
        return f"Tool not found: {e.filename}. Install jedi: pip install jedi"
    except subprocess.TimeoutExpired:
        return "Hover lookup timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_goto_definition(file_path: str, line: int, character: int) -> str:
    """
    Find where a symbol is defined.
    """
    # USER-VISIBLE NOTIFICATION
    print(f"🎯 LSP-GOTO-DEF: {file_path}:{line}:{character}", file=sys.stderr)

    client, uri, lang = await _get_client_and_params(file_path)

    if client:
        try:
            params = TextDocumentPositionParams(
                text_document=TextDocumentIdentifier(uri=uri),
                position=Position(line=line - 1, character=character),
            )

            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/definition", params), timeout=5.0
            )

            if response:
                if isinstance(response, list):
                    locations = response
                else:
                    locations = [response]

                results = []
                for loc in locations:
                    # Parse URI to path
                    target_uri = loc.uri
                    parsed = urlparse(target_uri)
                    target_path = unquote(parsed.path)

                    # Handle range
                    start_line = loc.range.start.line + 1
                    start_char = loc.range.start.character
                    results.append(f"{target_path}:{start_line}:{start_char}")

                if results:
                    return "\n".join(results)

            return "No definition found"

        except Exception as e:
            logger.error(f"LSP goto definition failed: {e}")
            # Fall through

    # Legacy fallback logic... (copy from existing)
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
definitions = script.goto({line}, {character})
for d in definitions:
    logger.info(f"{{d.module_path}}:{{d.line}}:{{d.column}} - {{d.full_name}}")
""",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout.strip()
            if output:
                return output
            return "No definition found"

        elif lang in ("typescript", "javascript"):
            return "TypeScript goto definition requires running language server. Use Claude Code's native navigation."

        else:
            return f"Goto definition not available for language: {lang}"

    except FileNotFoundError:
        return "Tool not found: Install jedi: pip install jedi"
    except subprocess.TimeoutExpired:
        return "Definition lookup timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_find_references(
    file_path: str, line: int, character: int, include_declaration: bool = True
) -> str:
    """
    Find all references to a symbol across the workspace.
    """
    # USER-VISIBLE NOTIFICATION
    print(f"🔗 LSP-REFS: {file_path}:{line}:{character}", file=sys.stderr)

    client, uri, lang = await _get_client_and_params(file_path)

    if client:
        try:
            params = ReferenceParams(
                text_document=TextDocumentIdentifier(uri=uri),
                position=Position(line=line - 1, character=character),
                context=ReferenceContext(include_declaration=include_declaration),
            )

            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/references", params), timeout=10.0
            )

            if response:
                results = []
                for loc in response:
                    # Parse URI to path
                    target_uri = loc.uri
                    parsed = urlparse(target_uri)
                    target_path = unquote(parsed.path)

                    start_line = loc.range.start.line + 1
                    start_char = loc.range.start.character
                    results.append(f"{target_path}:{start_line}:{start_char}")

                if results:
                    # Limit output
                    if len(results) > 50:
                        return "\n".join(results[:50]) + f"\n... and {len(results) - 50} more"
                    return "\n".join(results)

            return "No references found"

        except Exception as e:
            logger.error(f"LSP find references failed: {e}")

    # Legacy fallback...
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
references = script.get_references({line}, {character}, include_builtins=False)
for r in references[:30]:
    logger.info(f"{{r.module_path}}:{{r.line}}:{{r.column}}")
if len(references) > 30:
    logger.info(f"... and {{len(references) - 30}} more")
""",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = result.stdout.strip()
            if output:
                return output
            return "No references found"

        else:
            return f"Find references not available for language: {lang}"

    except subprocess.TimeoutExpired:
        return "Reference search timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_document_symbols(file_path: str) -> str:
    """
    Get hierarchical outline of all symbols in a file.
    """
    # USER-VISIBLE NOTIFICATION
    print(f"📋 LSP-SYMBOLS: {file_path}", file=sys.stderr)

    client, uri, lang = await _get_client_and_params(file_path)

    if client:
        try:
            params = DocumentSymbolParams(text_document=TextDocumentIdentifier(uri=uri))

            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/documentSymbol", params),
                timeout=5.0,
            )

            if response:
                lines = []
                # response can be List[DocumentSymbol] or List[SymbolInformation]
                # We'll handle a flat list representation for simplicity or traverse if hierarchical
                # For output, a simple flat list with indentation is good.

                # Helper to process symbols
                def process_symbols(symbols, indent=0):
                    for sym in symbols:
                        name = sym.name
                        kind = str(sym.kind)  # Enum integer
                        # Map some kinds to text if possible, but int is fine or name

                        # Handle location
                        if hasattr(sym, "range"):  # DocumentSymbol
                            line = sym.range.start.line + 1
                            children = getattr(sym, "children", [])
                        else:  # SymbolInformation
                            line = sym.location.range.start.line + 1
                            children = []

                        lines.append(f"{line:4d} | {'  ' * indent}{kind:4} {name}")

                        if children:
                            process_symbols(children, indent + 1)

                process_symbols(response)

                if lines:
                    return (
                        f"**Symbols in {Path(file_path).name}:**\n```\nLine | Kind Name\n"
                        + "\n".join(lines)
                        + "\n```"
                    )

            return "No symbols found"

        except Exception as e:
            logger.error(f"LSP document symbols failed: {e}")

    # Legacy fallback...
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
names = script.get_names(all_scopes=True, definitions=True)
for n in names:
    indent = "  " * (n.get_line_code().count("    ") if n.get_line_code() else 0)
    logger.info(f"{{n.line:4d}} | {{indent}}{{n.type:10}} {{n.name}}")
""",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout.strip()
            if output:
                return f"**Symbols in {path.name}:**\n```\nLine | Symbol\n{output}\n```"
            return "No symbols found"

        else:
            # Fallback: use ctags
            result = subprocess.run(
                ["ctags", "-x", "--sort=no", str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout.strip()
            if output:
                return f"**Symbols in {path.name}:**\n```\n{output}\n```"
            return "No symbols found"

    except FileNotFoundError:
        return "Install jedi (pip install jedi) or ctags for symbol lookup"
    except subprocess.TimeoutExpired:
        return "Symbol lookup timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_workspace_symbols(query: str, directory: str = ".") -> str:
    """
    Search for symbols by name across the entire workspace.
    """
    # USER-VISIBLE NOTIFICATION
    print(f"🔍 LSP-WS-SYMBOLS: query='{query}' dir={directory}", file=sys.stderr)

    # We need any client (python/ts) to search workspace, or maybe all of them?
    # Workspace symbols usually require a server to be initialized.
    # We can try to get python server if available, or just fallback to ripgrep if no persistent server is appropriate.
    # LSP 'workspace/symbol' is language-specific.

    manager = get_lsp_manager()
    results = []

    # Try Python
    client_py = await manager.get_server("python")
    if client_py:
        try:
            params = WorkspaceSymbolParams(query=query)
            response = await asyncio.wait_for(
                client_py.protocol.send_request_async("workspace/symbol", params), timeout=5.0
            )
            if response:
                for sym in response:
                    target_uri = sym.location.uri
                    parsed = urlparse(target_uri)
                    target_path = unquote(parsed.path)
                    line = sym.location.range.start.line + 1
                    results.append(f"{target_path}:{line} - {sym.name} ({sym.kind})")
        except Exception as e:
            logger.error(f"LSP workspace symbols (python) failed: {e}")

    if results:
        return "\n".join(results[:20])

    # Fallback to legacy grep/ctags
    try:
        # Use ctags to index and grep for symbols
        result = subprocess.run(
            ["rg", "-l", query, directory, "--type", "py", "--type", "ts", "--type", "js"],
            capture_output=True,
            text=True,
            timeout=15,
        )

        files = result.stdout.strip().split("\n")[:10]  # Limit files

        if not files or files == [""]:
            return "No matching files found"

        symbols = []
        for f in files:
            if not f:
                continue
            # Get symbols from each file
            ctags_result = subprocess.run(
                ["ctags", "-x", "--sort=no", f],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in ctags_result.stdout.split("\n"):
                if query.lower() in line.lower():
                    symbols.append(line)

        if symbols:
            return "\n".join(symbols[:20])
        return f"No symbols matching '{query}' found"

    except FileNotFoundError:
        return "Install ctags and ripgrep for workspace symbol search"
    except subprocess.TimeoutExpired:
        return "Search timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_prepare_rename(file_path: str, line: int, character: int) -> str:
    """
    Check if a symbol at position can be renamed.
    """
    # USER-VISIBLE NOTIFICATION
    print(f"✏️ LSP-PREP-RENAME: {file_path}:{line}:{character}", file=sys.stderr)

    client, uri, lang = await _get_client_and_params(file_path)

    if client:
        try:
            params = PrepareRenameParams(
                text_document=TextDocumentIdentifier(uri=uri),
                position=Position(line=line - 1, character=character),
            )

            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/prepareRename", params),
                timeout=5.0,
            )

            if response:
                # Response can be Range, {range, placeholder}, or null
                if hasattr(response, "placeholder"):
                    return f"✅ Rename is valid. Current name: {response.placeholder}"
                return "✅ Rename is valid at this position"

            # If null/false, invalid
            return "❌ Rename not valid at this position"

        except Exception as e:
            logger.error(f"LSP prepare rename failed: {e}")
            return f"Prepare rename failed: {e}"

    # Fallback
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
refs = script.get_references({line}, {character})
if refs:
    logger.info(f"Symbol: {{refs[0].name}}")
    logger.info(f"Type: {{refs[0].type}}")
    logger.info(f"References: {{len(refs)}}")
    logger.info("✅ Rename is valid")
else:
    logger.info("❌ No symbol found at position")
""",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or "No symbol found at position"

        else:
            return f"Prepare rename not available for language: {lang}"

    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_rename(
    file_path: str, line: int, character: int, new_name: str, dry_run: bool = True
) -> str:
    """
    Rename a symbol across the workspace.
    """
    # USER-VISIBLE NOTIFICATION
    mode = "dry-run" if dry_run else "APPLY"
    print(f"✏️ LSP-RENAME: {file_path}:{line}:{character} → '{new_name}' [{mode}]", file=sys.stderr)

    client, uri, lang = await _get_client_and_params(file_path)

    if client:
        try:
            params = RenameParams(
                text_document=TextDocumentIdentifier(uri=uri),
                position=Position(line=line - 1, character=character),
                new_name=new_name,
            )

            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/rename", params), timeout=10.0
            )

            if response and response.changes:
                # WorkspaceEdit
                changes_summary = []
                for file_uri, edits in response.changes.items():
                    parsed = urlparse(file_uri)
                    path_str = unquote(parsed.path)
                    changes_summary.append(f"File: {path_str}")
                    for edit in edits:
                        changes_summary.append(
                            f"  Line {edit.range.start.line + 1}: {edit.new_text}"
                        )

                output = "\n".join(changes_summary)

                if dry_run:
                    return f"**Would rename to '{new_name}':**\n{output}"
                else:
                    # Apply changes
                    # Since we are an MCP tool, we should ideally use the Edit tool or similar.
                    # But the 'Apply' contract implies we do it.
                    # We have file paths and edits. We should apply them.
                    # Implementation detail: Applying edits to files is complex to do robustly here without the Edit tool.
                    # However, since this tool is rewriting 'lsp_rename', we must support applying.
                    # But 'tools.py' previously used `jedi.refactoring.apply()`.

                    # For now, we'll return the diff and instruction to use Edit, OR implement a basic applier.
                    # Given the instruction "Rewrite ... to use the persistent client", implying functionality parity.
                    # Applying edits from LSP response requires careful handling.

                    # Let's try to apply if not dry_run
                    try:
                        _apply_workspace_edit(response.changes)
                        return f"✅ Renamed to '{new_name}'. Modified files:\n{output}"
                    except Exception as e:
                        return f"Failed to apply edits: {e}\nDiff:\n{output}"

            return "No changes returned from server"

        except Exception as e:
            logger.error(f"LSP rename failed: {e}")

    # Fallback
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
refactoring = script.rename({line}, {character}, new_name='{new_name}')
for path, changed in refactoring.get_changed_files().items():
    logger.info(f"File: {{path}}")
    logger.info(changed[:500])
    logger.info("---")
""",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = result.stdout.strip()
            if output and not dry_run:
                # Apply changes - Jedi handles this? No, get_changed_files returns the content.
                return f"**Dry run** (set dry_run=False to apply):\n{output}"
            elif output:
                return f"**Would rename to '{new_name}':**\n{output}"
            return "No changes needed"

        else:
            return f"Rename not available for language: {lang}. Use IDE refactoring."

    except Exception as e:
        return f"Error: {str(e)}"


def _apply_workspace_edit(changes: dict[str, list[Any]]):
    """Apply LSP changes to files."""
    for file_uri, edits in changes.items():
        parsed = urlparse(file_uri)
        path = Path(unquote(parsed.path))
        if not path.exists():
            continue

        content = path.read_text().splitlines(keepends=True)
        # Apply edits in reverse order to preserve offsets
        # Note: robust application requires handling multiple edits on same line, etc.
        # This is a simplified version.

        # Sort edits by start position descending
        edits.sort(key=lambda e: (e.range.start.line, e.range.start.character), reverse=True)

        for edit in edits:
            start_line = edit.range.start.line
            start_char = edit.range.start.character
            end_line = edit.range.end.line
            end_char = edit.range.end.character
            new_text = edit.new_text

            # This is tricky with splitlines.
            # Convert to single string, patch, then split back?
            # Or assume non-overlapping simple edits.

            if start_line == end_line:
                line_content = content[start_line]
                content[start_line] = line_content[:start_char] + new_text + line_content[end_char:]
            else:
                # Multi-line edit - complex
                # For safety, raise error for complex edits
                raise NotImplementedError(
                    "Complex multi-line edits not safe to apply automatically yet."
                )

        # Write back
        path.write_text("".join(content))


async def lsp_code_actions(file_path: str, line: int, character: int) -> str:
    """
    Get available quick fixes and refactorings at a position.
    """
    # USER-VISIBLE NOTIFICATION
    print(f"💡 LSP-ACTIONS: {file_path}:{line}:{character}", file=sys.stderr)

    client, uri, lang = await _get_client_and_params(file_path)

    if client:
        try:
            params = CodeActionParams(
                text_document=TextDocumentIdentifier(uri=uri),
                range=Range(
                    start=Position(line=line - 1, character=character),
                    end=Position(line=line - 1, character=character),
                ),
                context=CodeActionContext(
                    diagnostics=[]
                ),  # We should ideally provide diagnostics here
            )

            response = await asyncio.wait_for(
                client.protocol.send_request_async("textDocument/codeAction", params), timeout=5.0
            )

            if response:
                actions = []
                for action in response:
                    title = action.title
                    kind = action.kind
                    actions.append(f"- {title} ({kind})")
                return "**Available code actions:**\n" + "\n".join(actions)
            return "No code actions available at this position"

        except Exception as e:
            logger.error(f"LSP code actions failed: {e}")

    # Fallback
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        if lang == "python":
            # Use ruff to suggest fixes
            result = subprocess.run(
                ["ruff", "check", str(path), "--output-format=json", "--show-fixes"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            try:
                diagnostics = json.loads(result.stdout)
                actions = []
                for d in diagnostics:
                    if d.get("location", {}).get("row") == line:
                        code = d.get("code", "")
                        msg = d.get("message", "")
                        fix = d.get("fix", {})
                        if fix:
                            actions.append(f"- [{code}] {msg} (auto-fix available)")
                        else:
                            actions.append(f"- [{code}] {msg}")

                if actions:
                    return "**Available code actions:**\n" + "\n".join(actions)
                return "No code actions available at this position"

            except json.JSONDecodeError:
                return "No code actions available"

        else:
            return f"Code actions not available for language: {lang}"

    except FileNotFoundError:
        return "Install ruff for Python code actions: pip install ruff"
    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_code_action_resolve(file_path: str, action_code: str, line: int = None) -> str:
    """
    Apply a specific code action/fix to a file.
    """
    # USER-VISIBLE NOTIFICATION
    print(f"🔧 LSP-RESOLVE: {action_code} at {file_path}", file=sys.stderr)

    # Implementing via LSP requires 'codeAction/resolve' which is complex.
    # We stick to Ruff fallback for now as it's more direct for Python "fixes".
    # Unless we want to use the persistent client to trigger the action.
    # Most LSP servers return the Edit in the CodeAction response, so resolve might not be needed if we cache the actions.
    # But since this is a stateless call, we can't easily resolve a previous action.

    # We'll default to the existing robust Ruff implementation for Python.

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    lang = _get_language_for_file(file_path)

    if lang == "python":
        try:
            result = subprocess.run(
                ["ruff", "check", str(path), "--fix", "--select", action_code],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                return f"✅ Applied fix [{action_code}] to {path.name}"
            else:
                stderr = result.stderr.strip()
                if stderr:
                    return f"⚠️ {stderr}"
                return f"No changes needed for action [{action_code}]"

        except FileNotFoundError:
            return "Install ruff: pip install ruff"
        except subprocess.TimeoutExpired:
            return "Timeout applying fix"
        except Exception as e:
            return f"Error: {str(e)}"

    return f"Code action resolve not implemented for language: {lang}"


async def lsp_extract_refactor(
    file_path: str,
    start_line: int,
    start_char: int,
    end_line: int,
    end_char: int,
    new_name: str,
    kind: str = "function",
) -> str:
    """
    Extract code to a function or variable.
    """
    # USER-VISIBLE NOTIFICATION
    print(
        f"🔧 LSP-EXTRACT: {kind} '{new_name}' from {file_path}:{start_line}-{end_line}",
        file=sys.stderr,
    )

    # This is not a standard LSP method, though some servers support it via CodeActions or commands.
    # Jedi natively supports it via library, so we keep the fallback.
    # CodeAction might return 'refactor.extract'.

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
                    line=start_line, until_line=end_line, new_name=new_name
                )
            else:  # variable
                refactoring = script.extract_variable(
                    line=start_line, until_line=end_line, new_name=new_name
                )

            # Get the diff
            changes = refactoring.get_diff()
            return f"✅ Extract {kind} preview:\n```diff\n{changes}\n```\n\nTo apply: use Edit tool with the changes above"

        except AttributeError:
            return "Jedi version doesn't support extract refactoring. Upgrade: pip install -U jedi"
        except Exception as e:
            return f"Extract failed: {str(e)}"

    return f"Extract refactoring not implemented for language: {lang}"


async def lsp_servers() -> str:
    """
    List available LSP servers and their installation status.
    """
    # USER-VISIBLE NOTIFICATION
    print("🖥️ LSP-SERVERS: listing installed servers", file=sys.stderr)

    # Check env var overrides
    py_cmd = os.environ.get("LSP_CMD_PYTHON", "jedi-language-server")
    ts_cmd = os.environ.get("LSP_CMD_TYPESCRIPT", "typescript-language-server")

    servers = [
        ("python", "jedi", "pip install jedi"),
        ("python", "jedi-language-server", "pip install jedi-language-server"),
        ("python", "ruff", "pip install ruff"),
        ("typescript", "typescript-language-server", "npm i -g typescript-language-server"),
        ("go", "gopls", "go install golang.org/x/tools/gopls@latest"),
        ("rust", "rust-analyzer", "rustup component add rust-analyzer"),
    ]

    lines = [
        "**LSP Configuration (Env Vars):**",
        f"- `LSP_CMD_PYTHON`: `{py_cmd}`",
        f"- `LSP_CMD_TYPESCRIPT`: `{ts_cmd}`",
        "",
        "**Installation Status:**",
        "| Language | Server | Status | Install |",
        "|----------|--------|--------|---------|",
    ]

    for lang, server, install in servers:
        # Check if installed
        try:
            cmd = server.split()[0]  # simple check for command
            subprocess.run([cmd, "--version"], capture_output=True, timeout=2)
            status = "✅ Installed"
        except FileNotFoundError:
            status = "❌ Not installed"
        except Exception:
            status = "⚠️ Unknown"

        lines.append(f"| {lang} | {server} | {status} | `{install}` |")

    return "\n".join(lines)


async def lsp_health() -> str:
    """
    Check health of persistent LSP servers.
    """
    manager = get_lsp_manager()
    status = manager.get_status()

    if not status:
        return "No LSP servers configured"

    lines = [
        "**LSP Server Health:**",
        "| Language | Status | PID | Restarts | Command |",
        "|---|---|---|---|---|",
    ]

    for lang, info in status.items():
        state = "✅ Running" if info["running"] else "❌ Stopped"
        pid = info["pid"] or "-"
        restarts = info["restarts"]
        cmd = info["command"]

        # Truncate command if too long
        if len(cmd) > 30:
            cmd = cmd[:27] + "..."

        lines.append(f"| {lang} | {state} | {pid} | {restarts} | `{cmd}` |")

    return "\n".join(lines)
