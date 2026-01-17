import os
from pathlib import Path
from mcp_bridge.utils.cache import IOCache

async def write_file(path: str, content: str) -> str:
    """
    Write content to a file and invalidate cache.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    print(f"📝 WRITE: {path} ({len(content)} bytes)", file=sys.stderr)

    file_path = Path(path)
    try:
        # Ensure parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path.write_text(content, encoding="utf-8")
        
        # Invalidate cache for this path and its parent (directory listing)
        cache = IOCache.get_instance()
        cache.invalidate_path(str(file_path))
        cache.invalidate_path(str(file_path.parent))
        
        return f"Successfully wrote {len(content)} bytes to {path}"

    except Exception as e:
        return f"Error writing file {path}: {str(e)}"
