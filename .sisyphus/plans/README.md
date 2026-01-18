# Stravinsky Planning Documents

This directory contains planning documents for Stravinsky development.

## 📋 Available Plans

### [stravinsky-tui-improvement-plan.md](./stravinsky-tui-improvement-plan.md)

**Status**: DRAFT (Awaiting User Approval)

**Summary**: Comprehensive TUI improvement plan for Stravinsky

**Key Findings**:
- OMO has more features (10+ agents, 50+ tools, 23 hooks)
- Stravinsky has architectural advantages (zero overhead, native integration)
- Recommended approach: Build TUI using Python + Textual

**Implementation Timeline**:
- Phase 1: Event Pipeline (1-2 days)
- Phase 2: TUI Foundation (1-2 weeks)
- Phase 3: Visualization & UX (2-3 days)
- Phase 4: Optimization (1-2 days)
- **Total**: 2-3 weeks

**Key Features**:
- Multi-pane TUI (Agent Graph + Tool Timeline + Global Status)
- Real-time event streaming via hooks
- 60 FPS rendering with backpressure handling
- Keyboard shortcuts and search/filter
- Cost tracking and success rate metrics

---

## 🔗 Related Documentation

- [Stravinsky README](../../README.md)
- [Stravinsky CLAUDE.md](../../CLAUDE.md)
- [Stravinsky Architecture](../../ARCHITECTURE.md)

---

## 📊 Quick Reference

### TUI Stack

| Component | Technology |
|-----------|------------|
| UI Framework | Python + Textual |
| IPC | JSON Lines (stdout or UNIX socket) |
| Event Source | Stravinsky hooks + model proxy |
| Rendering | 60 FPS with batched updates |

### Key Files (Proposed)

| File | Purpose |
|------|---------|
| `mcp_bridge/hooks/event_emitter.py` | Emit structured events |
| `mcp_bridge/hooks/event_schema.py` | Event schema definitions |
| `mcp_bridge/hooks/event_queue.py` | Thread-safe event queue |
| `mcp_bridge/tui/main.py` | TUI entry point |
| `mcp_bridge/tui/agent_graph.py` | Agent graph widget |
| `mcp_bridge/tui/tool_timeline.py` | Tool timeline widget |
| `mcp_bridge/tui/global_status.py` | Global status widget |

### Success Criteria

✅ TUI displays live agent graph with tool timing
✅ TUI stays responsive under 10+ concurrent agents
✅ No measurable slowdown to orchestrator (<5% overhead)
✅ Event flood handled gracefully (sampling)
✅ UI renders at stable 60 FPS

---

**Last Updated**: January 17, 2026
