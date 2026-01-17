import os
from pathlib import Path
from mcp_bridge.utils.cache import IOCache

async def replace(
    path: str, 
    old_string: str, 
    new_string: str, 
    instruction: str,
    expected_replacements: int = 1
) -> str:
    """
    Replace text in a file and invalidate cache.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    print(f"🔄 REPLACE: {path} (instruction: {instruction})", file=sys.stderr)

    file_path = Path(path)
    if not file_path.exists():
        return f"Error: File not found: {path}"

    try:
        content = file_path.read_text(encoding="utf-8")
        
        # Check occurrence count
        count = content.count(old_string)
        if count == 0:
            return f"Error: Could not find exact match for old_string in {path}"
        
        if count != expected_replacements:
            return f"Error: Found {count} occurrences of old_string, but expected {expected_replacements} in {path}"

        # Perform replacement
        new_content = content.replace(old_string, new_string)
        file_path.write_text(new_content, encoding="utf-8")
        
        # Invalidate cache
        cache = IOCache.get_instance()
        cache.invalidate_path(str(file_path))
        
        return f"Successfully modified file: {path} ({count} replacements)."

    except Exception as e:
        return f"Error modifying file {path}: {str(e)}"
