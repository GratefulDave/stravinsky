"""
Edit error recovery hook.
Detects common mistakes in file editing and injects high-priority corrective directives.
"""

import re
from typing import Any, Dict, Optional

EDIT_ERROR_PATTERNS = [
    r"oldString and newString must be different",
    r"oldString not found",
    r"oldString found multiple times",
    r"Target content not found",
    r"Multiple occurrences of target content found",
]

EDIT_RECOVERY_PROMPT = """
> **[EDIT ERROR - IMMEDIATE ACTION REQUIRED]**
> You made an Edit mistake. STOP and do this NOW:
> 1. **READ** the file immediately to see its ACTUAL current state.
> 2. **VERIFY** what the content really looks like (your assumption was wrong).
> 3. **APOLOGIZE** briefly to the user for the error.
> 4. **CONTINUE** with corrected action based on the real file content.
> **DO NOT** attempt another edit until you've read and verified the file state.
"""

async def edit_error_recovery_hook(tool_name: str, arguments: Dict[str, Any], output: str) -> Optional[str]:
    """
    Analyzes tool output for edit errors and appends corrective directives.
    """
    # Check if this is an edit-related tool (handling both built-in and common MCP tools)
    edit_tools = ["replace_file_content", "multi_replace_file_content", "write_to_file", "edit_file", "Edit"]
    
    # We also check the output content for common patterns even if the tool name doesn't match perfectly
    is_edit_error = any(re.search(pattern, output, re.IGNORECASE) for pattern in EDIT_ERROR_PATTERNS)
    
    if is_edit_error or any(tool in tool_name for tool in edit_tools):
        if any(re.search(pattern, output, re.IGNORECASE) for pattern in EDIT_ERROR_PATTERNS):
            return output + EDIT_RECOVERY_PROMPT
            
    return None
