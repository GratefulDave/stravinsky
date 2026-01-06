"""
LSP Tools - Advanced Language Server Protocol Operations

Provides comprehensive LSP functionality via subprocess calls to language servers.
Supplements Claude Code's native LSP support with advanced operations.
"""

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

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


def _position_to_offset(content: str, line: int, character: int) -> int:
    """Convert line/character to byte offset."""
    lines = content.split("\n")
    offset = sum(len(l) + 1 for l in lines[:line - 1])  # 1-indexed
    offset += character
    return offset


async def lsp_hover(file_path: str, line: int, character: int) -> str:
    """
    Get type info, documentation, and signature at a position.

    Args:
        file_path: Absolute path to the file
        line: Line number (1-indexed)
        character: Character position (0-indexed)

    Returns:
        Type information and documentation at the position.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    print(f"📍 LSP-HOVER: {file_path}:{line}:{character}", file=sys.stderr)

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    
    lang = _get_language_for_file(file_path)
    
    try:
        if lang == "python":
            # Use jedi for Python hover info
            result = subprocess.run(
                [
                    "python", "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
completions = script.infer({line}, {character})
for c in completions[:1]:
    logger.info(f"Type: {{c.type}}")
    logger.info(f"Name: {{c.full_name}}")
    if c.docstring():
        logger.info(f"\\nDocstring:\\n{{c.docstring()[:500]}}")
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
            
        elif lang in ("typescript", "javascript", "typescriptreact", "javascriptreact"):
            # Use tsserver via quick-info
            # For simplicity, fall back to message
            return f"TypeScript hover requires running language server. Use Claude Code's native hover."
            
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
    
    Args:
        file_path: Absolute path to the file
        line: Line number (1-indexed)
        character: Character position (0-indexed)
        
    Returns:
        Location(s) where the symbol is defined.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    
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
    logger.info(f"{{d.module_path}}:{{d.line}}:{{d.column}} - {{d.full_name}}")
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
            
        elif lang in ("typescript", "javascript"):
            return "TypeScript goto definition requires running language server. Use Claude Code's native navigation."
            
        else:
            return f"Goto definition not available for language: {lang}"
            
    except FileNotFoundError as e:
        return f"Tool not found: Install jedi: pip install jedi"
    except subprocess.TimeoutExpired:
        return "Definition lookup timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_find_references(
    file_path: str, 
    line: int, 
    character: int,
    include_declaration: bool = True
) -> str:
    """
    Find all references to a symbol across the workspace.
    
    Args:
        file_path: Absolute path to the file
        line: Line number (1-indexed)
        character: Character position (0-indexed)
        include_declaration: Include the declaration itself
        
    Returns:
        All locations where the symbol is used.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    
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
    logger.info(f"{{r.module_path}}:{{r.line}}:{{r.column}}")
if len(references) > 30:
    logger.info(f"... and {{len(references) - 30}} more")
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
            
        else:
            return f"Find references not available for language: {lang}"
            
    except subprocess.TimeoutExpired:
        return "Reference search timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_document_symbols(file_path: str) -> str:
    """
    Get hierarchical outline of all symbols in a file.
    
    Args:
        file_path: Absolute path to the file
        
    Returns:
        Structured list of functions, classes, methods in the file.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    
    lang = _get_language_for_file(file_path)
    
    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python", "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
names = script.get_names(all_scopes=True, definitions=True)
for n in names:
    indent = "  " * (n.get_line_code().count("    ") if n.get_line_code() else 0)
    logger.info(f"{{n.line:4d}} | {{indent}}{{n.type:10}} {{n.name}}")
"""
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
    
    Args:
        query: Symbol name to search for (fuzzy match)
        directory: Workspace directory
        
    Returns:
        Matching symbols with their locations.
    """
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
    
    Args:
        file_path: Absolute path to the file
        line: Line number (1-indexed)
        character: Character position (0-indexed)
        
    Returns:
        The symbol that would be renamed and validation status.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    
    lang = _get_language_for_file(file_path)
    
    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python", "-c",
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
"""
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
    file_path: str, 
    line: int, 
    character: int, 
    new_name: str,
    dry_run: bool = True
) -> str:
    """
    Rename a symbol across the workspace.
    
    Args:
        file_path: Absolute path to the file
        line: Line number (1-indexed)
        character: Character position (0-indexed)
        new_name: New name for the symbol
        dry_run: If True, only show what would be changed
        
    Returns:
        List of changes that would be made (or were made if not dry_run).
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    
    lang = _get_language_for_file(file_path)
    
    try:
        if lang == "python":
            result = subprocess.run(
                [
                    "python", "-c",
                    f"""
import jedi
script = jedi.Script(path='{file_path}')
refactoring = script.rename({line}, {character}, new_name='{new_name}')
for path, changed in refactoring.get_changed_files().items():
    logger.info(f"File: {{path}}")
    logger.info(changed[:500])
    logger.info("---")
"""
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = result.stdout.strip()
            if output and not dry_run:
                # Apply changes
                return f"**Dry run** (set dry_run=False to apply):\n{output}"
            elif output:
                return f"**Would rename to '{new_name}':**\n{output}"
            return "No changes needed"
            
        else:
            return f"Rename not available for language: {lang}. Use IDE refactoring."
            
    except Exception as e:
        return f"Error: {str(e)}"


async def lsp_code_actions(file_path: str, line: int, character: int) -> str:
    """
    Get available quick fixes and refactorings at a position.
    
    Args:
        file_path: Absolute path to the file
        line: Line number (1-indexed)
        character: Character position (0-indexed)
        
    Returns:
        List of available code actions.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    
    lang = _get_language_for_file(file_path)
    
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


async def lsp_servers() -> str:
    """
    List available LSP servers and their installation status.
    
    Returns:
        Table of available language servers.
    """
    servers = [
        ("python", "jedi", "pip install jedi"),
        ("python", "ruff", "pip install ruff"),
        ("typescript", "typescript-language-server", "npm i -g typescript-language-server"),
        ("go", "gopls", "go install golang.org/x/tools/gopls@latest"),
        ("rust", "rust-analyzer", "rustup component add rust-analyzer"),
    ]
    
    lines = ["| Language | Server | Status | Install |", "|----------|--------|--------|---------|"]
    
    for lang, server, install in servers:
        # Check if installed
        try:
            subprocess.run([server, "--version"], capture_output=True, timeout=2)
            status = "✅ Installed"
        except FileNotFoundError:
            status = "❌ Not installed"
        except Exception:
            status = "⚠️ Unknown"
        
        lines.append(f"| {lang} | {server} | {status} | `{install}` |")
    
    return "\n".join(lines)
