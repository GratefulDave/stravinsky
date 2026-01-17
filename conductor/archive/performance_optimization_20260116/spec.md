# Track Specification: Performance Optimization & Context Management

## Overview
Reduce the overhead and perceived slowness of the `mcp_bridge` by implementing smart output truncation (to prevent context bloat) and I/O caching (to speed up redundant operations).

## Functional Requirements
### 1. Smart Output Management (Truncation)
- **Universal Cap:** Implement a hard character/token limit (e.g., 20,000 characters) for all tool outputs.
- **Auto-Tail:** Detect log-like file extensions (`.log`, `.out`, `.err`, `.txt` with log content) and read the *last* N lines by default when using `read_file`.
- **System Messaging:** Append a directive to truncated outputs (e.g., "Showing middle 50 lines... [Output truncated. Use offset/limit to see more]") to guide agents on how to retrieve missing context.

### 2. Smart I/O Caching
- **Implementation:** Implement a lightweight, in-memory cache for read-only operations (`read_file`, `list_directory`).
- **Short TTL:** Use a short time-to-live (e.g., 5-10 seconds) for cached results.
- **Write-Through Invalidation:** Automatically invalidate the cache for a specific path whenever a modifying tool (`write_file`, `replace`, `run_shell_command`) is executed on that path or directory.

## Non-Functional Requirements
- **Transparency:** The truncation must be visible to the LLM so it knows it doesn't have the full picture.
- **Low Latency:** The caching logic itself should introduce <1ms of overhead.

## Acceptance Criteria
- [ ] Large file reads are automatically truncated and include an instruction message.
- [ ] Log files are read from the tail by default when they exceed the limit.
- [ ] Repeated `list_directory` calls on the same path within 5 seconds show significant speed improvement (measured via logs).
- [ ] Writing to a file and immediately reading it back returns the *new* content (verifying cache invalidation).

## Out of Scope
- Migrating tools to Rust (handled in a separate track).
- Persistent disk-based caching.