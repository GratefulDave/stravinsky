# Stravinsky TUI Improvement Plan

**Status**: SUPERSEDED (See: [stravinsky-dashboard-integration.md](./stravinsky-dashboard-integration.md))

**Date**: January 17, 2026

**Author**: Stravinsky Research & Planning Team

---

## 📋 Executive Summary

### OMO (oh-my-opencode) Overview
- 10+ Specialized Agents with Sisyphus orchestrator
- NO Runtime TUI - Only setup wizard, no live visualization
- Rich Feature Set - 50+ tools, 23 hooks
- Architecture: CLI-based with rich terminal UX, but limited runtime visibility

### Stravinsky Overview
- 9 Native Agents - Task tool delegation pattern
- Advantages: Zero CLI overhead, Model proxy for async model calls, Semantic search with ChromaDB, Native Claude Code integration
- Feature Gaps: No TUI visualization, No planning triad, No agent permissions system, No interactive bash

### Key Finding
**OMO is more feature-rich and sophisticated, but Stravinsky has architectural advantages** (simpler, zero-overhead, native integration)

### CRITICAL DISCOVERY

**🎉 stravinsky-dashboard EXISTS and is COMPREHENSIVE!**

Found existing dashboard with:
- ✅ Real-time WebSocket streaming (Bun + TypeScript + SQLite)
- ✅ Event timeline with regex search
- ✅ Live pulse chart with time ranges (1m, 3m, 5m, 10m)
- ✅ Agent swim lanes for comparison
- ✅ Multi-criteria filtering (app, session, event type)
- ✅ Chat transcript viewer with advanced filters
- ✅ Theme management (12 predefined + custom themes)
- ✅ Mobile responsive design
- ✅ Toast notifications
- ✅ Auto-scroll with manual override

**Recommended Approach**: **Enhance existing dashboard** with Stravinsky-specific observability. Do NOT build from scratch.

---

## 🎯 Enhanced Implementation Plan

### Active Implementation: stravinsky-dashboard-integration.md

**Repository**: stravinsky-dashboard (separate repo)
**Branch**: feature/stravinsky-integration
**Current Status**: See implementation plan above

---

## 🚀 Next Steps

1. **Review** the active implementation plan: `stravinsky-dashboard-integration.md`
2. **Start** Phase 1: Stravinsky Model Proxy Integration
3. **Progress** through phases 2-6 at your own pace

---

**See active plan**: [stravinsky-dashboard-integration.md](./stravinsky-dashboard-integration.md)

**End of Plan**

