import os
from pathlib import Path
from typing import Optional
from mcp_bridge.utils.truncation import truncate_output, TruncationStrategy

from mcp_bridge.utils.cache import IOCache

async def read_file(
    path: str, 
    offset: int = 0, 
    limit: Optional[int] = None,
    max_chars: int = 20000
) -> str:
    """
    Read the contents of a file with smart truncation and log-awareness.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    print(f"📖 READ: {path} (offset={offset}, limit={limit})", file=sys.stderr)

    cache = IOCache.get_instance()
    cache_key = f"read_file:{os.path.realpath(path)}:{offset}:{limit}:{max_chars}"
    
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    file_path = Path(path)
    if not file_path.exists():
        return f"Error: File not found: {path}"
    
    if not file_path.is_file():
        return f"Error: Path is not a file: {path}"

    try:
        # Detect log files
        is_log = file_path.suffix.lower() in (".log", ".out", ".err")
        
        # Read lines
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Default behavior for log files if no limit/offset specified
        if is_log and limit is None and offset == 0 and total_lines > 100:
            # Default to last 100 lines for large logs
            offset = max(0, total_lines - 100)
            limit = 100
            strategy = TruncationStrategy.TAIL
            guidance = "Log file detected. Reading last 100 lines by default."
        else:
            strategy = TruncationStrategy.MIDDLE
            guidance = None

        # Apply line-based filtering
        start = offset
        end = total_lines
        if limit is not None:
            end = start + limit
        
        selected_lines = lines[start:end]
        content = "".join(selected_lines)
        
        # Apply character-based truncation (universal cap)
        result = truncate_output(
            content, 
            limit=max_chars, 
            strategy=strategy,
            custom_guidance=guidance
        )
        
        # If truncate_output didn't add guidance (because content < max_chars)
        # but we have log-based guidance, add it manually
        if guidance and guidance not in result:
            result = f"{result}\n\n[{guidance}]"
            
        # Cache for 5 seconds
        cache.set(cache_key, result)
            
        return result

    except Exception as e:
        return f"Error reading file {path}: {str(e)}"
