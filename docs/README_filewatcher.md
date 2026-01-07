# FileWatcher Integration Documentation

This directory contains comprehensive design documentation for integrating real-time file watching with CodebaseVectorStore to enable automatic incremental semantic indexing.

## Documents Overview

### 1. **filewatcher_quick_reference.md** (450 lines)
**Start here for practical usage**

Quick start guide for users. Covers:
- How to enable auto-indexing
- Common usage patterns
- Configuration options
- Troubleshooting
- Integration with Claude Code workflow

**Best for:** Developers who want to use file watching

### 2. **filewatcher_design_summary.md** (293 lines)
**Best for architecture understanding**

High-level design overview. Covers:
- Key design decisions and rationale
- Architecture diagram
- Module organization
- Implementation phases
- Error handling strategy
- Performance expectations

**Best for:** Understanding the overall design approach

### 3. **filewatcher_integration_design.md** (993 lines)
**Complete technical specification**

Full technical design document. Covers:
- Current state analysis
- FileWatcher class specification
- CodebaseVectorStore integration design
- Module-level cleanup design
- Server integration points
- Detailed lifecycle flow
- Configuration details
- Implementation checklist
- Error handling strategy
- Testing strategy
- Performance considerations
- Future enhancements
- Code snippets and examples

**Best for:** Implementation and detailed reference

---

## Reading Guide

### For Quick Implementation
1. Read: `filewatcher_quick_reference.md`
2. Review: `filewatcher_design_summary.md` (sections 1-3)
3. Implement: Follow `filewatcher_integration_design.md` (section 9 checklist)

### For Understanding the Design
1. Start: `filewatcher_design_summary.md`
2. Deep dive: `filewatcher_integration_design.md` (sections 1-7)
3. Reference: Code snippets in section 14

### For Integration Review
1. Check: `filewatcher_integration_design.md` section 6 (server integration)
2. Review: Lifecycle flow diagram (section 7)
3. Verify: Error handling strategy (section 10)

---

## Key Concepts

### FileWatcher
- Monitors project directory for file changes
- Uses `watchdog` library for cross-platform file system events
- Filters to code files only, skips ignored directories
- Debounces rapid changes (2 second window)

### CodebaseVectorStore Integration
- Owns FileWatcher instance (composition pattern)
- Can be enabled/disabled per store
- Auto-starts on first successful index (optional)
- Triggers incremental re-indexing on file changes

### Lifecycle Management
- **Level 1 (Store):** Per-store cleanup via `stop_watching()`
- **Level 2 (Module):** Batch cleanup via `cleanup_all_stores()`
- **Level 3 (Process):** Emergency cleanup via atexit handler

### Configuration
- **Auto-index on startup:** `STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true`
- **Per-store:** `watch_files=True, auto_start_watcher=True`
- **FileWatcher:** Adjustable debounce_seconds (default: 2.0)

---

## Implementation Status

The design is complete and ready for implementation. See checklist in `filewatcher_integration_design.md` section 9.

### Phases
1. **Phase 1 (1-2 hrs):** FileWatcher class + CodeFileEventHandler
2. **Phase 2 (1-2 hrs):** CodebaseVectorStore integration
3. **Phase 3 (1 hr):** Module-level cleanup + atexit
4. **Phase 4 (1 hr):** Server integration
5. **Phase 5 (1-2 hrs):** Tests + documentation

**Total estimated effort:** 5-9 hours

---

## File Locations

```
mcp_bridge/tools/
├── file_watcher.py              [NEW - to be created]
│   ├── CodeFileEventHandler
│   └── FileWatcher
│
└── semantic_search.py           [MODIFIED]
    ├── CodebaseVectorStore
    │   ├── Add: _watcher, _watch_files, _auto_start_watcher
    │   ├── Add: start_watching(), stop_watching()
    │   ├── Add: _on_file_changed()
    │   ├── Add: Async context manager
    │   └── Refactor: index_codebase() wrapper
    │
    └── Module-level
        ├── Add: cleanup_all_stores()
        ├── Add: atexit handler
        └── Update: get_store() signature

mcp_bridge/server.py            [MODIFIED]
└── async_main()
    ├── Add: Semantic indexing startup task
    └── Add: cleanup_all_stores() in finally block
```

---

## Related Documentation

- `/docs/semantic_indexing_analysis.md` - Current system state
- `/docs/semantic_indexing_quick_start.md` - User guide for semantic search
- `/CLAUDE.md` - Project overview and architecture
- `/mcp_bridge/tools/semantic_search.py` - Implementation (1754 lines)

---

## Quick Links

**Learn the design:** Start with `filewatcher_design_summary.md`

**Implement Phase 1:** Follow section 3 in `filewatcher_integration_design.md`

**Understand lifecycle:** See section 7 (Lifecycle Flow Diagram)

**Full checklist:** Section 9 in `filewatcher_integration_design.md`

**Code examples:** Section 14 (Appendix) in `filewatcher_integration_design.md`

---

## Technical Decisions

### Why watchdog?
- Industry standard, well-tested
- Cross-platform (Windows, macOS, Linux)
- Recursive directory watching
- Efficient file system monitoring

### Why lazy auto-start?
- Doesn't slow down store creation
- Confirms embedding provider works first
- User has explicit control
- Can be enabled globally via environment variable

### Why incremental-only?
- Much faster than full reindex
- Protects API quota usage
- Automatic detection of changed files
- Matches user expectations

### Why 2-second debounce?
- Prevents excessive re-indexing during editor autosave
- Groups multiple changes into single batch
- Balance between freshness and efficiency

---

## Next Steps

1. **Review design** - Read one or more documents above
2. **Get feedback** - Share with team for input
3. **Implementation** - Follow Phase 1-5 in the integration design
4. **Testing** - Use test strategy from section 11
5. **Documentation** - Update quick start guide with examples

---

## Questions?

Refer to the appropriate document:
- **"How do I use this?"** → `filewatcher_quick_reference.md`
- **"Why was it designed this way?"** → `filewatcher_design_summary.md`
- **"How do I implement it?"** → `filewatcher_integration_design.md`

---

Generated: 2026-01-07
Design status: Complete, ready for implementation
