import os
from pathlib import Path
from mcp_bridge.utils.cache import IOCache

async def list_directory(path: str) -> str:
    """
    List files and directories in a path with caching.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    print(f"📂 LIST: {path}", file=sys.stderr)

    cache = IOCache.get_instance()
    cache_key = f"list_dir:{os.path.realpath(path)}"
    
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    dir_path = Path(path)
    if not dir_path.exists():
        return f"Error: Directory not found: {path}"
    
    if not dir_path.is_dir():
        return f"Error: Path is not a directory: {path}"

    try:
        entries = []
        # Sort for deterministic output
        for entry in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            entry_type = "DIR" if entry.is_dir() else "FILE"
            entries.append(f"[{entry_type}] {entry.name}")
        
        result = "\n".join(entries) if entries else "(empty directory)"
        
        # Cache for 5 seconds
        cache.set(cache_key, result)
        
        return result

    except Exception as e:
        return f"Error listing directory {path}: {str(e)}"