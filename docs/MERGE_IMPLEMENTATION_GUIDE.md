# 3-Way Merge Implementation Guide

Complete guide for implementing the 3-way merge algorithm in Stravinsky.

---

## 1. Core Module Structure

```
mcp_bridge/
├── merge/
│   ├── __init__.py                 # Exports: three_way_merge(), MergeResult
│   ├── core.py                     # Main merge algorithm
│   ├── conflict_detector.py        # Conflict detection logic
│   ├── conflict_resolver.py        # Conflict markers & formatting
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── python_handler.py       # Python-specific merge
│   │   ├── markdown_handler.py     # Markdown-specific merge
│   │   └── json_handler.py         # JSON-specific merge
│   └── utils.py                    # Helper functions
```

---

## 2. Type Definitions

```python
# mcp_bridge/merge/core.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Literal
from enum import Enum

class MergeStatus(str, Enum):
    """Result status of merge operation."""
    SUCCESS = "success"
    CONFLICT = "conflict"
    ERROR = "error"

class ConflictSeverity(str, Enum):
    """How severe is the conflict?"""
    CRITICAL = "critical"      # Cannot auto-merge, needs review
    HIGH = "high"              # Likely needs review
    MEDIUM = "medium"          # Might auto-merge
    LOW = "low"                # Can auto-merge

@dataclass
class Conflict:
    """Single conflict marker."""
    line_start: int
    line_end: int
    base_lines: List[str]
    ours_lines: List[str]
    theirs_lines: List[str]
    severity: ConflictSeverity
    reason: str

@dataclass
class MergeResult:
    """Result of 3-way merge operation."""
    merged_content: Optional[str]      # Merged text (None if error)
    status: MergeStatus                 # success/conflict/error
    conflicts: List[Conflict]           # List of conflicts (if any)
    confidence: float                   # 0.0-1.0 confidence score
    message: str                        # Human-readable status
    metadata: Dict = None               # File type, file size, etc.

@dataclass
class MergeOptions:
    """Configuration for merge behavior."""
    preserve_user_imports: bool = True
    preserve_user_functions: bool = True
    auto_accept_threshold: float = 0.95
    backup_before_write: bool = True
    conflict_marker_format: Literal["git", "custom"] = "custom"
```

---

## 3. Main Merge Function

```python
# mcp_bridge/merge/core.py

from pathlib import Path
from typing import Union
import logging

logger = logging.getLogger(__name__)

async def three_way_merge(
    base_content: str,
    ours_content: str,
    theirs_content: str,
    file_path: Union[str, Path] = None,
    options: MergeOptions = None,
) -> MergeResult:
    """
    Perform 3-way merge of three file versions.

    Args:
        base_content: Original content (from base version)
        ours_content: Current content (user modifications)
        theirs_content: New content (from framework update)
        file_path: Optional path for type detection
        options: Merge configuration

    Returns:
        MergeResult with merged content and conflict info

    Raises:
        ValueError: If inputs are invalid
    """

    options = options or MergeOptions()

    # Step 1: Validate inputs
    try:
        _validate_inputs(base_content, ours_content, theirs_content)
    except ValueError as e:
        logger.error(f"Merge validation failed: {e}")
        return MergeResult(
            merged_content=None,
            status=MergeStatus.ERROR,
            conflicts=[],
            confidence=0.0,
            message=str(e),
        )

    # Step 2: Detect file type
    file_type = _detect_file_type(file_path, base_content)

    # Step 3: Route to type-specific handler
    handler = _get_handler(file_type)

    try:
        merged_content, conflicts = await handler.merge(
            base_content, ours_content, theirs_content, options
        )

        # Step 4: Determine status
        if not conflicts:
            status = MergeStatus.SUCCESS
            confidence = 1.0
            message = "Merge successful, no conflicts"
        else:
            status = MergeStatus.CONFLICT
            confidence = _calculate_confidence(conflicts, file_type)
            message = f"Merge has {len(conflicts)} conflict(s)"

            # Check if auto-mergeable with high confidence
            if confidence >= options.auto_accept_threshold:
                # Automatically resolve conflicts
                merged_content = _auto_resolve_conflicts(
                    merged_content, conflicts, base_content, ours_content, theirs_content
                )
                status = MergeStatus.SUCCESS
                message = f"Merge auto-resolved with {confidence:.1%} confidence"

        return MergeResult(
            merged_content=merged_content,
            status=status,
            conflicts=conflicts,
            confidence=confidence,
            message=message,
            metadata={
                "file_type": file_type,
                "base_size": len(base_content),
                "ours_size": len(ours_content),
                "theirs_size": len(theirs_content),
                "merged_size": len(merged_content) if merged_content else 0,
            },
        )

    except Exception as e:
        logger.exception(f"Merge failed with exception: {e}")
        return MergeResult(
            merged_content=ours_content,  # Fallback: keep current version
            status=MergeStatus.ERROR,
            conflicts=[],
            confidence=0.0,
            message=f"Merge error: {e}",
        )


def _validate_inputs(base: str, ours: str, theirs: str) -> None:
    """Validate merge inputs."""
    if not isinstance(base, str) or not isinstance(ours, str) or not isinstance(theirs, str):
        raise ValueError("All inputs must be strings")

    if len(base) == 0 or len(ours) == 0 or len(theirs) == 0:
        logger.warning("One or more inputs are empty")


def _detect_file_type(file_path: Union[str, Path], content: str) -> str:
    """Detect file type from path or content."""
    if file_path:
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".py":
            return "python"
        elif suffix == ".md":
            return "markdown"
        elif suffix == ".json":
            return "json"

    # Content-based detection
    if content.strip().startswith("{"):
        return "json"
    elif content.strip().startswith("---"):
        return "markdown"
    elif content.strip().startswith("import") or content.strip().startswith("def "):
        return "python"

    return "text"


def _get_handler(file_type: str):
    """Get appropriate merge handler for file type."""
    from .handlers import python_handler, markdown_handler, json_handler

    handlers = {
        "python": python_handler.PythonMergeHandler(),
        "markdown": markdown_handler.MarkdownMergeHandler(),
        "json": json_handler.JsonMergeHandler(),
    }

    return handlers.get(file_type, _TextMergeHandler())


def _calculate_confidence(conflicts: List[Conflict], file_type: str) -> float:
    """Calculate merge confidence based on conflict severity."""
    if not conflicts:
        return 1.0

    severity_scores = {
        ConflictSeverity.CRITICAL: 0.0,
        ConflictSeverity.HIGH: 0.2,
        ConflictSeverity.MEDIUM: 0.6,
        ConflictSeverity.LOW: 0.9,
    }

    avg_severity = sum(
        severity_scores.get(c.severity, 0.5) for c in conflicts
    ) / len(conflicts)

    return max(0.0, min(1.0, avg_severity))


def _auto_resolve_conflicts(
    merged: str,
    conflicts: List[Conflict],
    base: str,
    ours: str,
    theirs: str,
) -> str:
    """Automatically resolve low-confidence conflicts."""
    for conflict in conflicts:
        if conflict.severity == ConflictSeverity.LOW:
            # Use heuristic: prefer THEIRS if user didn't modify
            if _is_user_customized(base, ours, conflict):
                # Keep user version
                pass
            else:
                # Use framework version
                pass

    return merged
```

---

## 4. Python Handler

```python
# mcp_bridge/merge/handlers/python_handler.py

import ast
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class PythonMergeHandler:
    """Merge handler for Python files."""

    async def merge(
        self, base: str, ours: str, theirs: str, options
    ) -> Tuple[str, List[Conflict]]:
        """Merge Python files using AST analysis."""

        conflicts = []

        try:
            # Parse all versions
            base_ast = ast.parse(base) if base.strip() else None
            ours_ast = ast.parse(ours) if ours.strip() else None
            theirs_ast = ast.parse(theirs) if theirs.strip() else None

        except SyntaxError as e:
            logger.error(f"Python syntax error: {e}")
            conflicts.append(
                Conflict(
                    line_start=e.lineno or 0,
                    line_end=e.lineno or 0,
                    base_lines=[],
                    ours_lines=[],
                    theirs_lines=[],
                    severity=ConflictSeverity.CRITICAL,
                    reason=f"Syntax error: {e}",
                )
            )
            return ours, conflicts

        # Extract components
        base_imports = self._extract_imports(base_ast, base)
        ours_imports = self._extract_imports(ours_ast, ours)
        theirs_imports = self._extract_imports(theirs_ast, theirs)

        base_funcs = self._extract_functions(base_ast, base)
        ours_funcs = self._extract_functions(ours_ast, ours)
        theirs_funcs = self._extract_functions(theirs_ast, theirs)

        # Merge imports
        merged_imports = self._merge_imports(
            base_imports, ours_imports, theirs_imports
        )

        # Merge functions
        merged_funcs, func_conflicts = self._merge_functions(
            base_funcs, ours_funcs, theirs_funcs, options
        )
        conflicts.extend(func_conflicts)

        # Preserve user-added functions
        for func_name, func_def in ours_funcs.items():
            if func_name not in base_funcs and func_name not in merged_funcs:
                merged_funcs[func_name] = func_def

        # Reconstruct file
        merged = self._reconstruct_python(merged_imports, merged_funcs)

        return merged, conflicts

    def _extract_imports(self, tree: ast.Module, content: str) -> dict:
        """Extract import statements."""
        imports = {}

        if not tree:
            return imports

        lines = content.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.name] = {
                        "type": "import",
                        "line": node.lineno,
                        "text": lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                    }
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    key = f"from {module} import {alias.name}"
                    imports[key] = {
                        "type": "from_import",
                        "line": node.lineno,
                        "text": lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                    }

        return imports

    def _extract_functions(self, tree: ast.Module, content: str) -> dict:
        """Extract function definitions."""
        functions = {}

        if not tree:
            return functions

        lines = content.split("\n")

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                start_line = node.lineno
                end_line = node.end_lineno or start_line

                func_text = "\n".join(lines[start_line - 1 : end_line])

                functions[node.name] = {
                    "node": node,
                    "start_line": start_line,
                    "end_line": end_line,
                    "text": func_text,
                }

        return functions

    def _merge_imports(self, base: dict, ours: dict, theirs: dict) -> dict:
        """Merge imports using union semantics."""
        merged = {}

        # Start with THEIRS (framework)
        merged.update(theirs)

        # Add OURS imports not in THEIRS
        for key, value in ours.items():
            if key not in merged:
                merged[key] = value

        return merged

    def _merge_functions(
        self, base: dict, ours: dict, theirs: dict, options
    ) -> Tuple[dict, List[Conflict]]:
        """Merge functions with conflict detection."""
        merged = {}
        conflicts = []

        for func_name, theirs_def in theirs.items():
            if func_name in ours:
                # Both have this function
                base_def = base.get(func_name)

                if base_def and self._is_different(base_def["text"], ours[func_name]["text"]):
                    # User modified - check if THEIRS also modified
                    if self._is_different(base_def["text"], theirs_def["text"]):
                        # Both modified - CONFLICT
                        conflicts.append(
                            Conflict(
                                line_start=base_def.get("start_line", 0),
                                line_end=base_def.get("end_line", 0),
                                base_lines=base_def["text"].split("\n"),
                                ours_lines=ours[func_name]["text"].split("\n"),
                                theirs_lines=theirs_def["text"].split("\n"),
                                severity=ConflictSeverity.HIGH,
                                reason=f"Function '{func_name}' modified by both user and framework",
                            )
                        )
                        # Use OURS (preserve user version)
                        merged[func_name] = ours[func_name]
                    else:
                        # Only user modified - keep OURS
                        merged[func_name] = ours[func_name]
                else:
                    # User didn't modify - use THEIRS
                    merged[func_name] = theirs_def
            else:
                # Only framework has it - add it
                merged[func_name] = theirs_def

        return merged, conflicts

    def _is_different(self, text1: str, text2: str) -> bool:
        """Check if two code texts are different (ignoring whitespace)."""
        norm1 = "\n".join(line.strip() for line in text1.split("\n") if line.strip())
        norm2 = "\n".join(line.strip() for line in text2.split("\n") if line.strip())
        return norm1 != norm2

    def _reconstruct_python(self, imports: dict, functions: dict) -> str:
        """Reconstruct Python file from components."""
        lines = []

        # Add imports
        for import_key, import_info in imports.items():
            lines.append(import_info["text"])

        # Add blank line
        if imports and functions:
            lines.append("")

        # Add functions
        for func_name, func_def in functions.items():
            lines.append("")
            lines.append(func_def["text"])
            lines.append("")

        return "\n".join(lines)
```

---

## 5. Markdown Handler

```python
# mcp_bridge/merge/handlers/markdown_handler.py

import re
from typing import List, Dict, Tuple
import yaml
import logging

logger = logging.getLogger(__name__)

class MarkdownMergeHandler:
    """Merge handler for Markdown files."""

    async def merge(
        self, base: str, ours: str, theirs: str, options
    ) -> Tuple[str, List[Conflict]]:
        """Merge Markdown files with frontmatter support."""

        conflicts = []

        # Parse all versions
        base_meta, base_body = self._parse_markdown(base)
        ours_meta, ours_body = self._parse_markdown(ours)
        theirs_meta, theirs_body = self._parse_markdown(theirs)

        # Merge metadata
        merged_meta, meta_conflicts = self._merge_metadata(
            base_meta, ours_meta, theirs_meta
        )
        conflicts.extend(meta_conflicts)

        # Split body into sections
        base_sections = self._split_by_headers(base_body)
        ours_sections = self._split_by_headers(ours_body)
        theirs_sections = self._split_by_headers(theirs_body)

        # Merge sections
        merged_sections, section_conflicts = self._merge_sections(
            base_sections, ours_sections, theirs_sections
        )
        conflicts.extend(section_conflicts)

        # Preserve user-added sections
        for header, content in ours_sections.items():
            if header not in base_sections and header not in merged_sections:
                merged_sections[header] = content

        # Reconstruct
        merged = self._reconstruct_markdown(merged_meta, merged_sections)

        return merged, conflicts

    def _parse_markdown(self, content: str) -> Tuple[dict, str]:
        """Parse YAML frontmatter and body."""
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        try:
            meta = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            logger.error(f"YAML parse error: {e}")
            meta = {}

        body = parts[2].strip()

        return meta or {}, body

    def _merge_metadata(
        self, base: dict, ours: dict, theirs: dict
    ) -> Tuple[dict, List[Conflict]]:
        """Merge YAML metadata."""
        merged = {}
        conflicts = []

        for key, theirs_value in theirs.items():
            ours_value = ours.get(key)
            base_value = base.get(key)

            if key in ours:
                if base_value and base_value != ours_value:
                    # User customized
                    if ours_value != theirs_value:
                        # Both modified - check if compatible
                        if type(ours_value) != type(theirs_value):
                            conflicts.append(
                                Conflict(
                                    line_start=0,
                                    line_end=0,
                                    base_lines=[str(base_value)],
                                    ours_lines=[str(ours_value)],
                                    theirs_lines=[str(theirs_value)],
                                    severity=ConflictSeverity.MEDIUM,
                                    reason=f"Metadata '{key}' type mismatch",
                                )
                            )
                        merged[key] = ours_value
                    else:
                        merged[key] = ours_value
                else:
                    merged[key] = theirs_value
            else:
                merged[key] = theirs_value

        # Preserve user custom keys
        for key, value in ours.items():
            if key not in base and key not in theirs:
                merged[key] = value

        return merged, conflicts

    def _split_by_headers(self, content: str) -> Dict[str, str]:
        """Split content by markdown headers."""
        sections = {}
        current_header = "__intro__"
        current_content = []

        for line in content.split("\n"):
            if line.startswith("#"):
                if current_content:
                    sections[current_header] = "\n".join(current_content).strip()
                    current_content = []

                current_header = line.strip()
            else:
                current_content.append(line)

        if current_content:
            sections[current_header] = "\n".join(current_content).strip()

        return sections

    def _merge_sections(
        self, base: dict, ours: dict, theirs: dict
    ) -> Tuple[dict, List[Conflict]]:
        """Merge body sections."""
        merged = {}
        conflicts = []

        for header, theirs_content in theirs.items():
            if header in ours:
                base_content = base.get(header, "")

                if base_content and base_content != ours[header]:
                    # User modified
                    if base_content != theirs_content:
                        # Both modified - line-based diff
                        merged_content, has_conflict = self._three_way_diff(
                            base_content, ours[header], theirs_content
                        )

                        if has_conflict:
                            conflicts.append(
                                Conflict(
                                    line_start=0,
                                    line_end=0,
                                    base_lines=base_content.split("\n"),
                                    ours_lines=ours[header].split("\n"),
                                    theirs_lines=theirs_content.split("\n"),
                                    severity=ConflictSeverity.MEDIUM,
                                    reason=f"Section '{header}' has conflicting changes",
                                )
                            )

                        merged[header] = merged_content
                    else:
                        merged[header] = ours[header]
                else:
                    merged[header] = theirs_content
            else:
                merged[header] = theirs_content

        return merged, conflicts

    def _three_way_diff(self, base: str, ours: str, theirs: str) -> Tuple[str, bool]:
        """Simple 3-way diff for text sections."""
        base_lines = base.split("\n")
        ours_lines = ours.split("\n")
        theirs_lines = theirs.split("\n")

        # If no differences, return THEIRS
        if base_lines == ours_lines == theirs_lines:
            return theirs, False

        # If user didn't change, return THEIRS
        if base_lines == ours_lines:
            return theirs, False

        # If framework didn't change, return OURS
        if base_lines == theirs_lines:
            return ours, False

        # All different - conflict
        return f"<<<< ours\n{ours}\n====\n{theirs}\n>>>>", True

    def _reconstruct_markdown(self, meta: dict, sections: dict) -> str:
        """Reconstruct markdown from components."""
        result = []

        if meta:
            result.append("---")
            result.append(yaml.dump(meta, default_flow_style=False))
            result.append("---")

        for header, content in sections.items():
            if header != "__intro__":
                result.append(header)

            result.append(content)
            result.append("")

        return "\n".join(result).strip()
```

---

## 6. JSON Handler

```python
# mcp_bridge/merge/handlers/json_handler.py

import json
from typing import List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class JsonMergeHandler:
    """Merge handler for JSON files."""

    async def merge(
        self, base: str, ours: str, theirs: str, options
    ) -> Tuple[str, List[Conflict]]:
        """Merge JSON files."""

        conflicts = []

        try:
            base_obj = json.loads(base) if base.strip() else {}
            ours_obj = json.loads(ours) if ours.strip() else {}
            theirs_obj = json.loads(theirs) if theirs.strip() else {}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            conflicts.append(
                Conflict(
                    line_start=0,
                    line_end=0,
                    base_lines=[],
                    ours_lines=[],
                    theirs_lines=[],
                    severity=ConflictSeverity.CRITICAL,
                    reason=f"JSON parse error: {e}",
                )
            )
            return ours, conflicts

        # Deep merge
        merged_obj, merge_conflicts = self._deep_merge(base_obj, ours_obj, theirs_obj, path="")
        conflicts.extend(merge_conflicts)

        # Format result
        merged = json.dumps(merged_obj, indent=2)

        return merged, conflicts

    def _deep_merge(
        self, base: Any, ours: Any, theirs: Any, path: str
    ) -> Tuple[Any, List[Conflict]]:
        """Recursively merge JSON objects."""

        conflicts = []

        # Base case: primitives
        if not isinstance(theirs, dict):
            if base != ours:
                # User customized
                if ours != theirs:
                    # Both modified - CONFLICT
                    conflicts.append(
                        Conflict(
                            line_start=0,
                            line_end=0,
                            base_lines=[str(base)],
                            ours_lines=[str(ours)],
                            theirs_lines=[str(theirs)],
                            severity=ConflictSeverity.HIGH,
                            reason=f"Value conflict at {path}",
                        )
                    )

            return theirs, conflicts

        # Recursive case: objects
        result = {}

        for key, theirs_value in theirs.items():
            base_value = base.get(key) if isinstance(base, dict) else None
            ours_value = ours.get(key) if isinstance(ours, dict) else None

            new_path = f"{path}.{key}" if path else key

            if isinstance(theirs_value, dict):
                merged, key_conflicts = self._deep_merge(
                    base_value or {},
                    ours_value or {},
                    theirs_value,
                    new_path,
                )
                result[key] = merged
                conflicts.extend(key_conflicts)

            elif isinstance(theirs_value, list):
                result[key], list_conflicts = self._merge_arrays(
                    base_value or [], ours_value or [], theirs_value, new_path
                )
                conflicts.extend(list_conflicts)

            else:
                # Primitive
                if ours_value is not None:
                    if base_value != ours_value:
                        # User customized
                        if ours_value != theirs_value:
                            # Both modified - CONFLICT
                            conflicts.append(
                                Conflict(
                                    line_start=0,
                                    line_end=0,
                                    base_lines=[str(base_value)],
                                    ours_lines=[str(ours_value)],
                                    theirs_lines=[str(theirs_value)],
                                    severity=ConflictSeverity.HIGH,
                                    reason=f"Value conflict at {new_path}",
                                )
                            )
                        result[key] = ours_value
                    else:
                        result[key] = theirs_value
                else:
                    result[key] = theirs_value

        # Preserve user-added keys
        if isinstance(ours, dict):
            for key, ours_value in ours.items():
                if key not in base and key not in theirs:
                    result[key] = ours_value

        return result, conflicts

    def _merge_arrays(
        self, base: list, ours: list, theirs: list, path: str
    ) -> Tuple[list, List[Conflict]]:
        """Merge JSON arrays (union semantics)."""

        conflicts = []

        # If all identical, return THEIRS
        if base == ours == theirs:
            return theirs, conflicts

        # If user didn't modify, return THEIRS
        if base == ours:
            return theirs, conflicts

        # If framework didn't modify, return OURS
        if base == theirs:
            return ours, conflicts

        # Check if order-sensitive (unlikely for configs)
        # For now, use union semantics
        result = list(theirs)
        for item in ours:
            if item not in result:
                result.append(item)

        return result, conflicts
```

---

## 7. Integration with Update System

```python
# mcp_bridge/hooks/update_manager.py

from pathlib import Path
from typing import Optional
from .merge import three_way_merge, MergeResult
import logging
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

class HookUpdateManager:
    """Manages hook updates with 3-way merge."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.hooks_dir = self.project_path / ".claude" / "hooks"
        self.backup_dir = self.project_path / ".stravinsky" / "backups"

    async def update_hook(
        self,
        hook_name: str,
        new_content: str,
        base_version: Optional[str] = None,
    ) -> MergeResult:
        """
        Update a hook file with automatic merging.

        Args:
            hook_name: Name of hook to update
            new_content: New content from framework
            base_version: Version string for backup tracking

        Returns:
            MergeResult with merge status and conflicts
        """

        hook_path = self.hooks_dir / hook_name
        if not hook_path.exists():
            # New hook - just write it
            hook_path.parent.mkdir(parents=True, exist_ok=True)
            hook_path.write_text(new_content)
            logger.info(f"Created new hook: {hook_name}")
            return MergeResult(
                merged_content=new_content,
                status="success",
                conflicts=[],
                confidence=1.0,
                message=f"New hook created: {hook_name}",
            )

        # Load versions
        current_content = hook_path.read_text()
        base_content = self._load_base_version(hook_name, base_version)

        # Merge
        merge_result = await three_way_merge(
            base_content,
            current_content,
            new_content,
            hook_path,
        )

        # Handle result
        if merge_result.status == "success":
            # Backup current version
            self._backup_hook(hook_path, current_content)

            # Write merged version
            hook_path.write_text(merge_result.merged_content)
            logger.info(f"Hook updated: {hook_name}")

        elif merge_result.status == "conflict":
            # Create conflict marker file
            conflict_path = hook_path.with_suffix(f"{hook_path.suffix}.CONFLICT")
            conflict_path.write_text(merge_result.merged_content)

            logger.warning(f"Merge conflict in {hook_name} - see {conflict_path}")

            # Notify user
            self._notify_conflict(hook_name, merge_result)

        return merge_result

    def _load_base_version(self, hook_name: str, version: Optional[str]) -> str:
        """Load base version of hook from version control."""
        if version:
            # Try to load from git history
            try:
                import subprocess

                result = subprocess.run(
                    ["git", "show", f"{version}:.claude/hooks/{hook_name}"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_path,
                )

                if result.returncode == 0:
                    return result.stdout

            except Exception as e:
                logger.error(f"Failed to load base version {version}: {e}")

        # Fallback: return empty string (new file scenario)
        return ""

    def _backup_hook(self, hook_path: Path, content: str) -> None:
        """Backup hook before updating."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{hook_path.name}.{timestamp}.bak"

        backup_path.write_text(content)
        logger.debug(f"Backed up hook to {backup_path}")

    def _notify_conflict(self, hook_name: str, result: MergeResult) -> None:
        """Notify user of merge conflicts."""
        logger.warning(
            f"⚠️  Merge conflict in hook '{hook_name}'\n"
            f"   Conflicts: {len(result.conflicts)}\n"
            f"   Review: {hook_name}.CONFLICT\n"
            f"   Run: stravinsky merge --resolve {hook_name}"
        )
```

---

## 8. Testing

```python
# tests/merge/test_merge.py

import pytest
from mcp_bridge.merge import three_way_merge

@pytest.mark.asyncio
async def test_merge_no_conflict():
    """Test auto-merge with no conflicts."""
    base = "def hook():\n    return True\n"
    ours = "def hook():\n    return True\n"
    theirs = "def hook():\n    # Updated\n    return True\n"

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "success"
    assert len(result.conflicts) == 0

@pytest.mark.asyncio
async def test_merge_with_conflict():
    """Test merge with conflicting changes."""
    base = "def hook():\n    return allow()\n"
    ours = "def hook():\n    if user_check():\n        return allow()\n"
    theirs = "def hook():\n    if admin_check():\n        return allow()\n"

    result = await three_way_merge(base, ours, theirs)

    assert result.status == "conflict"
    assert len(result.conflicts) > 0

@pytest.mark.asyncio
async def test_preserve_user_imports():
    """Test that user-added imports are preserved."""
    base = "from pathlib import Path\n"
    ours = "import logging\nfrom pathlib import Path\n"
    theirs = "from pathlib import Path\nfrom typing import Dict\n"

    result = await three_way_merge(base, ours, theirs)

    assert "import logging" in result.merged_content
    assert "from typing import Dict" in result.merged_content
```

---

## 9. Deployment Checklist

- [ ] Implement core merge algorithm in `mcp_bridge/merge/core.py`
- [ ] Implement Python handler in `handlers/python_handler.py`
- [ ] Implement Markdown handler in `handlers/markdown_handler.py`
- [ ] Implement JSON handler in `handlers/json_handler.py`
- [ ] Integrate with update manager in `hooks/update_manager.py`
- [ ] Add comprehensive test coverage
- [ ] Documentation and examples
- [ ] Performance benchmarking
- [ ] Integration with CI/CD pipeline
- [ ] User notification system
- [ ] Rollback mechanism
- [ ] Production deployment

---

## 10. Performance Optimization

For large files:
- Use line-based diffs instead of AST for speed
- Cache parsed ASTs to avoid re-parsing
- Limit conflict detection to changed regions
- Stream processing for JSON arrays > 1MB

---

## 11. References

- [Git 3-way merge](https://github.com/git/git/blob/master/ll-merge.c)
- [AST-based merging](https://www.semanticscholar.org/paper)
- [Conflict resolution patterns](https://git-scm.com/docs/merge-strategies)
