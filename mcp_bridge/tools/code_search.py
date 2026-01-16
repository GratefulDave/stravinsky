"""
LSP Tools - Language Server Protocol Operations

These tools provide LSP functionality for Claude Code via subprocess calls
to language servers. Claude Code has native LSP support, so these serve as
supplementary utilities for advanced operations.
"""

import json
import subprocess
from pathlib import Path


async def lsp_diagnostics(file_path: str, severity: str = "all") -> str:
    """
    Get diagnostics (errors, warnings) for a file using language server.

    For TypeScript/JavaScript, uses `tsc` or `biome`.
    For Python, uses `pyright` or `ruff`.

    Args:
        file_path: Path to the file to analyze
        severity: Filter by severity (error, warning, information, hint, all)

    Returns:
        Formatted diagnostics output.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    print(f"🩺 LSP-DIAG: file={file_path} severity={severity}", file=sys.stderr)

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    
    suffix = path.suffix.lower()
    
    try:
        if suffix in (".ts", ".tsx", ".js", ".jsx"):
            # Use TypeScript compiler for diagnostics
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", "--pretty", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout + result.stderr
            if not output.strip():
                return "No diagnostics found"
            return output
            
        elif suffix == ".py":
            # Use ruff for Python diagnostics
            result = subprocess.run(
                ["ruff", "check", str(path), "--output-format=concise"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout + result.stderr
            if not output.strip():
                return "No diagnostics found"
            return output
            
        else:
            return f"No diagnostics available for file type: {suffix}"
            
    except FileNotFoundError as e:
        return f"Tool not found: {e.filename}. Install required tools."
    except subprocess.TimeoutExpired:
        return "Diagnostics timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def check_ai_comment_patterns(file_path: str) -> str:
    """
    Detect AI-generated or placeholder comment patterns that indicate incomplete work.

    Patterns detected:
    - # TODO: implement, # FIXME, # placeholder
    - // TODO, // FIXME, // placeholder
    - AI-style verbose comments: "This function handles...", "This method is responsible for..."
    - Placeholder phrases: "implement this", "add logic here", "your code here"

    Args:
        file_path: Path to the file to check

    Returns:
        List of detected AI-style patterns with line numbers, or "No AI patterns detected"
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    print(f"🤖 AI-CHECK: {file_path}", file=sys.stderr)

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    # Patterns that indicate AI-generated or placeholder code
    ai_patterns = [
        # Placeholder comments
        r"#\s*(TODO|FIXME|XXX|HACK):\s*(implement|add|placeholder|your code)",
        r"//\s*(TODO|FIXME|XXX|HACK):\s*(implement|add|placeholder|your code)",
        # AI-style verbose descriptions
        r"#\s*This (function|method|class) (handles|is responsible for|manages|processes)",
        r"//\s*This (function|method|class) (handles|is responsible for|manages|processes)",
        r'"""This (function|method|class) (handles|is responsible for|manages|processes)',
        # Placeholder implementations
        r"pass\s*#\s*(TODO|implement|placeholder)",
        r"raise NotImplementedError.*implement",
        # Common AI filler phrases
        r"#.*\b(as needed|as required|as appropriate|if necessary)\b",
        r"//.*\b(as needed|as required|as appropriate|if necessary)\b",
    ]

    import re

    try:
        content = path.read_text()
        lines = content.split("\n")
        findings = []

        for i, line in enumerate(lines, 1):
            for pattern in ai_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(f"  Line {i}: {line.strip()[:80]}")
                    break

        if findings:
            return f"AI/Placeholder patterns detected in {file_path}:\n" + "\n".join(findings)
        return "No AI patterns detected"

    except Exception as e:
        return f"Error reading file: {str(e)}"


async def ast_grep_search(pattern: str, directory: str = ".", language: str = "") -> str:
    """
    Search codebase using ast-grep for structural patterns.

    ast-grep uses AST-aware pattern matching, finding code by structure
    rather than just text. More precise than regex for code search.

    Args:
        pattern: ast-grep pattern to search for
        directory: Directory to search in
        language: Filter by language (typescript, python, rust, etc.)

    Returns:
        Matched code locations and snippets.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    lang_info = f" lang={language}" if language else ""
    print(f"🔍 AST-GREP: pattern='{pattern[:50]}...'{lang_info}", file=sys.stderr)

    try:
        cmd = ["sg", "run", "-p", pattern, directory]
        if language:
            cmd.extend(["--lang", language])
        cmd.append("--json")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0 and not result.stdout:
            return result.stderr or "No matches found"
        
        # Parse and format JSON output
        try:
            matches = json.loads(result.stdout)
            if not matches:
                return "No matches found"
            
            lines = []
            for match in matches[:20]:  # Limit to 20 results
                file_path = match.get("file", "unknown")
                start_line = match.get("range", {}).get("start", {}).get("line", 0)
                text = match.get("text", "")
                lines.append(f"{file_path}:{start_line}: {text[:100]}")
            
            return "\n".join(lines)
        except json.JSONDecodeError:
            return result.stdout or "No matches found"
            
    except FileNotFoundError:
        return "ast-grep (sg) not found. Install with: npm install -g @ast-grep/cli"
    except subprocess.TimeoutExpired:
        return "Search timed out"
    except Exception as e:
        return f"Error: {str(e)}"


from mcp_bridge.native_search import native_glob_files, native_grep_search


async def grep_search(pattern: str, directory: str = ".", file_pattern: str = "") -> str:
    """
    Fast text search using ripgrep (or native Rust implementation if available).

    Args:
        pattern: Search pattern (supports regex)
        directory: Directory to search in
        file_pattern: Glob pattern to filter files (e.g., "*.py", "*.ts")

    Returns:
        Matched lines with file paths and line numbers.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    glob_info = f" glob={file_pattern}" if file_pattern else ""
    print(f"🔎 GREP: pattern='{pattern[:50]}'{glob_info} dir={directory}", file=sys.stderr)

    # Try native implementation first (currently doesn't support file_pattern filter in the same way)
    # If file_pattern is provided, we still use rg for now as it's more flexible with globs
    if not file_pattern:
        native_results = native_grep_search(pattern, directory)
        if native_results is not None:
            if not native_results:
                return "No matches found"
            
            lines = []
            for r in native_results[:50]:
                lines.append(f"{r['path']}:{r['line']}: {r['content']}")
            
            if len(native_results) > 50:
                lines.append(f"... and more (showing first 50 matches)")
            
            return "\n".join(lines)

    try:
        cmd = ["rg", "--line-number", "--max-count=50", pattern, directory]
        if file_pattern:
            cmd.extend(["--glob", file_pattern])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        output = result.stdout
        if not output.strip():
            return "No matches found"
        
        # Limit output lines
        lines = output.strip().split("\n")
        if len(lines) > 50:
            lines = lines[:50]
            lines.append("... and more (showing first 50 matches)")
        
        return "\n".join(lines)
        
    except FileNotFoundError:
        return "ripgrep (rg) not found. Install with: brew install ripgrep"
    except subprocess.TimeoutExpired:
        return "Search timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def glob_files(pattern: str, directory: str = ".") -> str:
    """
    Find files matching a glob pattern (uses native Rust implementation if available).

    Args:
        pattern: Glob pattern (e.g., "**/*.py", "src/**/*.ts")
        directory: Base directory for search

    Returns:
        List of matching file paths.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    print(f"📁 GLOB: pattern='{pattern}' dir={directory}", file=sys.stderr)

    # Try native implementation first
    native_results = native_glob_files(pattern, directory)
    if native_results is not None:
        if not native_results:
            return "No files found"
        
        # Limit output
        lines = native_results
        if len(lines) > 100:
            lines = lines[:100]
            lines.append(f"... and {len(native_results) - 100} more files")
        
        return "\n".join(lines)

    try:
        cmd = ["fd", "--type", "f", "--glob", pattern, directory]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        output = result.stdout
        if not output.strip():
            return "No files found"
        
        # Limit output
        lines = output.strip().split("\n")
        if len(lines) > 100:
            lines = lines[:100]
            lines.append(f"... and {len(lines) - 100} more files")
        
        return "\n".join(lines)
        
    except FileNotFoundError:
        return "fd not found. Install with: brew install fd"
    except subprocess.TimeoutExpired:
        return "Search timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def ast_grep_replace(
    pattern: str,
    replacement: str,
    directory: str = ".",
    language: str = "",
    dry_run: bool = True
) -> str:
    """
    Replace code patterns using ast-grep's AST-aware replacement.
    
    ast-grep uses structural pattern matching for precise code transformations.
    More reliable than text-based search/replace for refactoring.
    
    Args:
        pattern: ast-grep pattern to search for (e.g., "console.log($A)")
        replacement: Replacement pattern (e.g., "logger.debug($A)")
        directory: Directory to search in
        language: Filter by language (typescript, python, rust, etc.)
        dry_run: If True (default), only show what would change without applying
        
    Returns:
        Preview of changes or confirmation of applied changes.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    mode = "dry-run" if dry_run else "APPLY"
    lang_info = f" lang={language}" if language else ""
    print(f"🔄 AST-REPLACE: '{pattern[:30]}' → '{replacement[:30]}'{lang_info} [{mode}]", file=sys.stderr)

    try:
        # Build command
        cmd = ["sg", "run", "-p", pattern, "-r", replacement, directory]
        if language:
            cmd.extend(["--lang", language])
        
        if dry_run:
            # Show what would change
            cmd.append("--json")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0 and not result.stdout:
                return result.stderr or "No matches found"
            
            try:
                matches = json.loads(result.stdout)
                if not matches:
                    return "No matches found for pattern"
                
                lines = [f"**Dry run** - {len(matches)} matches found:"]
                for match in matches[:15]:
                    file_path = match.get("file", "unknown")
                    start_line = match.get("range", {}).get("start", {}).get("line", 0)
                    original = match.get("text", "")[:80]
                    lines.append(f"\n`{file_path}:{start_line}`")
                    lines.append(f"```\n{original}\n```")
                
                if len(matches) > 15:
                    lines.append(f"\n... and {len(matches) - 15} more matches")
                
                lines.append("\n**To apply changes**, call with `dry_run=False`")
                return "\n".join(lines)
                
            except json.JSONDecodeError:
                return result.stdout or "No matches found"
        else:
            # Actually apply the changes
            cmd_apply = ["sg", "run", "-p", pattern, "-r", replacement, directory, "--update-all"]
            if language:
                cmd_apply.extend(["--lang", language])
            
            result = subprocess.run(
                cmd_apply,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode == 0:
                return f"✅ Successfully applied replacement:\n- Pattern: `{pattern}`\n- Replacement: `{replacement}`\n\n{result.stdout}"
            else:
                return f"❌ Failed to apply replacement:\n{result.stderr}"
            
    except FileNotFoundError:
        return "ast-grep (sg) not found. Install with: npm install -g @ast-grep/cli"
    except subprocess.TimeoutExpired:
        return "Replacement timed out"
    except Exception as e:
        return f"Error: {str(e)}"

