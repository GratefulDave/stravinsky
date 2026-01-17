from enum import Enum
from typing import Optional

class TruncationStrategy(Enum):
    MIDDLE = "middle"
    TAIL = "tail"

def truncate_output(
    text: str, 
    limit: int = 20000, 
    strategy: TruncationStrategy = TruncationStrategy.MIDDLE,
    custom_guidance: Optional[str] = None
) -> str:
    """
    Truncates text to a specific limit using the chosen strategy. 
    
    Args:
        text: The string to truncate.
        limit: Max characters allowed.
        strategy: How to truncate (MIDDLE or TAIL).
        custom_guidance: Optional extra message for the agent.
    """
    if len(text) <= limit:
        return text

    # Standard guidance messages
    guidance = "\n\n[Output truncated. "
    if custom_guidance:
        guidance += custom_guidance + " "
    
    if strategy == TruncationStrategy.TAIL:
        # Show the END of the file
        truncated_text = text[-limit:]
        msg = f"{guidance}Showing last {limit} characters. Use offset/limit parameters to read specific parts of the file.]"
        return f"... [TRUNCATED] ...\n{truncated_text}{msg}"
    
    else:  # MIDDLE strategy
        # Show start and end, snip the middle
        half_limit = limit // 2
        start_part = text[:half_limit]
        end_part = text[-half_limit:]
        msg = f"{guidance}Showing first and last {half_limit} characters. Use offset/limit parameters to read specific parts of the file.]"
        return f"{start_part}\n\n[... content truncated ...]\n\n{end_part}{msg}"
