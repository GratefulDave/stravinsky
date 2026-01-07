# MCP Tool Call Logging - Documentation Index

Complete exploration and implementation guide for adding formatted output logging to MCP tool calls.

## Quick Start

**Read first (2 minutes)**:
- [`QUICK_REFERENCE_INJECTION_POINTS.md`](./QUICK_REFERENCE_INJECTION_POINTS.md) - TL;DR version with priorities and exact line numbers

**Then read (10 minutes)**:
- [`CALL_FLOW_DIAGRAM.txt`](./CALL_FLOW_DIAGRAM.txt) - Visual flow diagrams showing where code executes

**Deep dive (30 minutes)**:
- [`MCP_TOOL_CALL_INJECTION_POINTS.md`](./MCP_TOOL_CALL_INJECTION_POINTS.md) - Complete analysis with code examples

## Document Descriptions

### 1. QUICK_REFERENCE_INJECTION_POINTS.md
**Purpose**: Quick lookup guide for developers  
**Contents**:
- Critical injection points ranked by priority
- Already-done items (no changes needed)
- Nice-to-have improvements
- All file paths (absolute)
- Key imports available
- Output format template
- Lines to modify (ranked by impact)
- Validation checklist

**Best for**: Finding "where do I add code?" questions

### 2. CALL_FLOW_DIAGRAM.txt
**Purpose**: Visual understanding of execution flow  
**Contents**:
- ASCII flow diagrams showing:
  - User calls tool → MCP dispatches → implementation
  - Parallel flows for Gemini and OpenAI invocation
  - Task spawn flow
- Key metrics (lines to modify, files to touch, risk level)
- What's already working (✅ checklist)
- What needs enhancement (? checklist)
- Example output before/after

**Best for**: Understanding "what happens when?" questions

### 3. MCP_TOOL_CALL_INJECTION_POINTS.md
**Purpose**: Comprehensive technical reference  
**Contents**:
- Priority 1-4 injection points with exact line numbers
- Current code at each location
- Proposed enhancements with rationale
- Code examples ready to copy-paste
- Integration points summary table
- Recommended implementation order (3 phases)
- Key constants available for import
- Output format specification

**Best for**: Implementation details and decision-making

## The Problem

MCP tool calls (especially `agent_spawn`, `invoke_gemini`, `invoke_openai`) lack consistent formatted output logging showing:
- Which agent/model is being invoked
- What task or prompt is being executed
- What the cost tier is (cheap/medium/expensive)
- What the task ID is for tracking

## The Solution

Add formatted output at key injection points following the specification:
```
{emoji} {agent_type}:{model}('{description}') {status}
task_id={task_id}
```

Example:
```
🟢 explore:gemini-3-flash('Find auth handler') ⏳
task_id=agent_abc123
```

## Key Findings

### Already Working
- ✅ `agent_spawn` output format is perfect
- ✅ `invoke_gemini` prints formatted stderr
- ✅ `invoke_openai` prints formatted stderr
- ✅ Cost tier emoji system fully implemented
- ✅ Model name mappings all in place

### Needs Enhancement (Priority)
1. HIGH: `server.py:313-316` - agent_spawn dispatcher logging
2. HIGH: `server.py:98-141` - _format_tool_log enhancement
3. MEDIUM: `agent_manager.py:295` - _execute_agent stderr notification
4. LOW: `background_tasks.py:132-137` - task_spawn result formatting
5. LOW: `background_tasks.py:117-127` - spawn subprocess notification

## Implementation Scope

- **Lines to modify**: 15-20 total
- **Files to touch**: 3 files
- **Risk level**: LOW (logging only)
- **Backwards compatibility**: 100%
- **Testing impact**: Minimal

## File Locations

All changes in `/Users/davidandrews/PycharmProjects/stravinsky/`:

```
mcp_bridge/
├── server.py                    (Lines 313-316, 98-141, 354-360)
└── tools/
    ├── agent_manager.py         (Line 295)
    ├── model_invoke.py          (Already complete)
    └── background_tasks.py      (Lines 132-137, 117-127)
```

## Output Format Specification

### Emoji Meanings
- `🟢` = Cheap (gemini-3-flash, haiku)
- `🔵` = Medium (gemini-3-pro-high)
- `🟣` = Expensive (gpt-5.2, opus)
- `🟠` = Claude (sonnet via CLI)
- `🔮` = Gemini model invoked
- `🧠` = OpenAI model invoked
- `⏳` = Spawned, waiting

### Standard Format
```
{emoji} {action}:{agent_type}:{model}('{description}') {status}
task_id={task_id}
```

## Available Constants

From `mcp_bridge/tools/agent_manager.py`:

```python
# Display models mapping
AGENT_DISPLAY_MODELS = {
    "explore": "gemini-3-flash",
    "dewey": "gemini-3-flash",
    "frontend": "gemini-3-pro-high",
    "delphi": "gpt-5.2",
    ...
}

# Cost tiers
AGENT_COST_TIERS = {
    "explore": "CHEAP",
    "frontend": "MEDIUM",
    "delphi": "EXPENSIVE",
    ...
}

# Emoji indicators
COST_TIER_EMOJI = {
    "CHEAP": "🟢",
    "MEDIUM": "🔵",
    "EXPENSIVE": "🟣",
}

# Helper functions
def get_agent_emoji(agent_type: str) -> str
def get_model_emoji(model_name: str) -> str
```

## Next Steps

1. **Read**: Start with `QUICK_REFERENCE_INJECTION_POINTS.md`
2. **Understand**: Review `CALL_FLOW_DIAGRAM.txt` to see execution flow
3. **Implement**: Use code examples from `MCP_TOOL_CALL_INJECTION_POINTS.md`
4. **Validate**: Follow validation checklist in `QUICK_REFERENCE_INJECTION_POINTS.md`
5. **Test**: Run agent spawning to verify output

## Questions?

Refer to the appropriate document:
- "Where do I add code?" → `QUICK_REFERENCE_INJECTION_POINTS.md`
- "How does execution flow?" → `CALL_FLOW_DIAGRAM.txt`
- "Show me the code examples" → `MCP_TOOL_CALL_INJECTION_POINTS.md`
- "What's the current status?" → `MCP_TOOL_CALL_INJECTION_POINTS.md` Priority sections

---

**Last Updated**: 2026-01-07  
**Status**: Exploration Complete - Ready for Implementation
