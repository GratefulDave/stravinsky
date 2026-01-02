"""
Tool output truncator hook.
Limits the size of tool outputs to prevent context bloat.
"""

from typing import Any, Dict, Optional

async def output_truncator_hook(tool_name: str, arguments: Dict[str, Any], output: str) -> Optional[str]:
    """
    Truncates tool output if it exceeds a certain length.
    """
    MAX_LENGTH = 30000 # 30k characters limit
    
    if len(output) > MAX_LENGTH:
        truncated = output[:MAX_LENGTH]
        summary = f"\n\n... (Result truncated from {len(output)} chars to {MAX_LENGTH} chars) ..."
        return truncated + summary
        
    return None
