import asyncio
import time
import os
from pathlib import Path
from mcp_bridge.tools.list_directory import list_directory
from mcp_bridge.tools.read_file import read_file
from mcp_bridge.utils.cache import IOCache

async def benchmark_list_directory():
    print("\n--- Benchmarking list_directory ---")
    cache = IOCache.get_instance()
    cache.clear()
    
    # Measure first call (uncached)
    start = time.perf_counter()
    await list_directory(".")
    first_duration = (time.perf_counter() - start) * 1000
    print(f"First call (uncached): {first_duration:.2f}ms")
    
    # Measure second call (cached)
    start = time.perf_counter()
    await list_directory(".")
    second_duration = (time.perf_counter() - start) * 1000
    print(f"Second call (cached):   {second_duration:.2f}ms")
    
    reduction = ((first_duration - second_duration) / first_duration) * 100
    print(f"Latency reduction: {reduction:.1f}%")
    return reduction

async def benchmark_read_file_truncation():
    print("\n--- Benchmarking read_file truncation ---")
    
    # Create a 1MB file
    large_file = Path("benchmark_large.txt")
    large_file.write_text("A" * (1024 * 1024))
    
    try:
        # Measure content length vs original
        content = await read_file(str(large_file), max_chars=20000)
        original_size = 1024 * 1024
        truncated_size = len(content)
        
        savings = ((original_size - truncated_size) / original_size) * 100
        print(f"Original size:  {original_size} chars")
        print(f"Truncated size: {truncated_size} chars")
        print(f"Token savings (approx): {savings:.1f}%")
        return savings
    finally:
        if large_file.exists():
            large_file.unlink()

async def main():
    await benchmark_list_directory()
    await benchmark_read_file_truncation()

if __name__ == "__main__":
    asyncio.run(main())
