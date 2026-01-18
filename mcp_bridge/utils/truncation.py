from enum import Enum
from typing import Optional
import logging

try:
    import stravinsky_native
    from stravinsky_native import truncator
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False
    logging.warning("stravinsky_native not found. Native truncation unavailable.")

class TruncationStrategy(Enum):
    MIDDLE = "middle"
    TAIL = "tail"
    AUTO_TAIL = "auto_tail" # New line-based strategy

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

def auto_tail_logs(content: str, head_lines: int = 100, tail_lines: int = 100) -> str:
    """
    Smart truncation for logs using native Rust implementation.
    Keeps the first N lines (setup/config) and last M lines (recent errors).
    """
    if NATIVE_AVAILABLE:
        try:
            return truncator.auto_tail(content, head_lines, tail_lines)
        except Exception as e:
            logging.error(f"Native truncation failed: {e}")
            # Fallback to python implementation
            
    # Python fallback
    lines = content.splitlines()
    if len(lines) <= head_lines + tail_lines:
        return content
        
    head = "\n".join(lines[:head_lines])
    tail = "\n".join(lines[-tail_lines:])
    hidden = len(lines) - (head_lines + tail_lines)
    
    return f"{head}\n\n<... {hidden} lines truncated (fallback) ...>\n\n{tail}"