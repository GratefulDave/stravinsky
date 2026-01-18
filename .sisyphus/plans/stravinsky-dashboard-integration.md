# Stravinsky Dashboard Integration Plan

**Status**: IN PROGRESS

**Branch**: `feature/stravinsky-integration` (stravinsky-dashboard repository)

**Date**: January 17, 2026

**Author**: Stravinsky Integration Team

---

## 📋 Executive Summary

### Discovery: Existing Dashboard Capabilities

The stravinsky-dashboard already provides **comprehensive observability infrastructure**:

**Built Features:**
- ✅ Real-time WebSocket streaming (Bun server)
- ✅ Event timeline with regex search
- ✅ Live pulse chart with time ranges (1m, 3m, 5m, 10m)
- ✅ Agent swim lanes for comparison
- ✅ Multi-criteria filtering (app, session, event type)
- ✅ Chat transcript viewer with advanced filters
- ✅ Theme management (12 predefined + custom)
- ✅ Mobile responsive design
- ✅ Toast notifications
- ✅ Auto-scroll with manual override

**Architecture:**
- Server: Bun + TypeScript + SQLite (WAL mode)
- Client: Vue 3 + TypeScript + Vite + Tailwind CSS
- Hooks: Python + Astral uv
- Protocol: HTTP POST + WebSocket broadcast

---

## 🎯 Integration Strategy

### Core Principle
**Enhance existing dashboard** with Stravinsky-specific observability. Do NOT rebuild from scratch.

### Implementation Phases

### Phase 1: Stravinsky Model Proxy Integration (1-2 days)
**Objective**: Capture model invocation metrics (tokens, cost, latency)

**Tasks**:
1. [ ] Add Stravinsky metrics to event payload schema
2. [ ] Create Stravinsky metrics hook script
3. [ ] Integrate with Stravinsky model proxy events
4. [ ] Add cost/tokens fields to database schema
5. [ ] Test metrics flow end-to-end

**Deliverables**:
- Modified `send_event.py` with new flags
- New `stravinsky_metrics.py` hook script
- Updated `db.ts` with Stravinsky columns
- End-to-end metrics working

---

### Phase 2: Agent Hierarchy Visualization (2-3 days)
**Objective**: Visualize parent-child agent relationships (nested spawning)

**Tasks**:
1. [ ] Create AgentHierarchy.vue component
2. [ ] Parse parent-child relationships from events
3. [ ] Implement collapsible tree visualization
4. [ ] Add to App.vue (toggle view)
5. [ ] Style with indent levels and connecting lines

**Deliverables**:
- AgentHierarchy.vue component
- Hierarchy parsing logic
- Tree visualization with expand/collapse
- Integrated into dashboard

---

### Phase 3: Cost Metrics Dashboard (2-3 days)
**Objective**: Display real-time cost tracking and model performance

**Tasks**:
1. [ ] Create CostMetrics.vue component
2. [ ] Calculate total cost per session/app
3. [ ] Create per-model cost breakdown chart
4. [ ] Add token usage line chart
5. [ ] Add to App.vue (new view)

**Deliverables**:
- CostMetrics.vue component
- Real-time cost aggregation
- Model comparison charts
- Integrated into dashboard

---

### Phase 4: Tool Execution Timing (1-2 days)
**Objective**: Display tool duration and identify slow operations

**Tasks**:
1. [ ] Calculate tool duration (PostToolUse - PreToolUse)
2. [ ] Display duration in EventRow.vue
3. [ ] Add color coding (fast/medium/slow)
4. [ ] Add configurable thresholds
5. [ ] Highlight slow tools

**Deliverables**:
- Duration calculation logic
- Color-coded timing display
- Slow tool alerts

---

### Phase 5: Parallel Execution Visualization (2-3 days)
**Objective**: Visualize concurrent tool calls and agent parallelism

**Tasks**:
1. [ ] Detect overlapping time ranges
2. [ ] Add parallel operation indicator
3. [ ] Show concurrent tool count
4. [ ] Add parallelism metrics to LivePulseChart
5. [ ] Visualize parallel tool execution

**Deliverables**:
- Parallel operation detection
- Visual indicators
- Parallelism metrics

---

### Phase 6: Model Performance Dashboard (2-3 days)
**Objective**: Compare model performance (Haiku vs Sonnet, Gemini, GPT)

**Tasks**:
1. [ ] Create ModelPerformance.vue component
2. [ ] Calculate per-model metrics (latency, error rate)
3. [ ] Add side-by-side comparison view
4. [ ] Add latency percentile tracking
5. [ ] Add to App.vue (toggle view)

**Deliverables**:
- ModelPerformance.vue component
- Per-model metrics
- Model comparison charts
- Integrated into dashboard

---

## 📊 Integration Points

### 1. Event Payload Extension

**File**: `.claude/hooks/send_event.py`

**Add to event_data**:
\`\`\`python
"stravinsky": {
    "cost_usd": float,           # Cost in USD
    "input_tokens": int,        # Input token count
    "output_tokens": int,       # Output token count
    "total_tokens": int,       # Total tokens
    "model": str,              # Model name
    "provider": str,           # anthropic/openai/gemini
    "agent_type": str,         # Agent type
    "task_id": str,            # Task tracking ID
    "parent_session_id": str,   # Parent session for hierarchy
    "hierarchy_level": int,     # Nesting depth
}
\`\`\`

### 2. Database Schema Extension

**File**: `apps/server/src/db.ts`

**Optional: Add new columns**:
\`\`\`typescript
ALTER TABLE events ADD COLUMN stravinsky TEXT; -- JSON with above fields
ALTER TABLE events ADD COLUMN stravinsky_cost_usd REAL; -- Separate for filtering
\`\`\`

### 3. New Hook Script

**File**: `.claude/hooks/stravinsky_metrics.py`

**Purpose**: Query Stravinsky internal metrics on Stop/SubagentStop events

**Implementation**:
- Query Stravinsky's metrics database or memory
- Calculate total cost and tokens
- Send to dashboard via send_event.py

---

## ✅ Success Criteria

- [ ] Model invocation events captured with tokens and cost
- [ ] Agent hierarchy visualized with parent-child relationships
- [ ] Cost metrics displayed in real-time
- [ ] Tool execution timing shown with color coding
- [ ] Parallel operations visualized and measured
- [ ] Model performance dashboard working
- [ ] All views toggleable in App.vue
- [ ] No breaking changes to existing features

---

## 🚀 Next Steps

### Immediate Actions:
1. Start Phase 1 (Model Proxy Integration)
2. Test event flow from Stravinsky to dashboard
3. Iterate through phases 2-6

### Dependencies:
- Stravinsky MCP server running
- Stravinsky model proxy active
- Dashboard server running (Bun, port 4000)
- Dashboard client connected (Vite, port 5173)

---

**End of Plan**

