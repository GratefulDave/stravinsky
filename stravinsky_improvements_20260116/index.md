# Stravinsky Orchestration & Semantic Search Improvements

**Status:** Ready for Implementation
**Estimated Effort:** 16-22 hours
**Priority:** HIGH

## Overview
Comprehensive improvements to Stravinsky MCP bridge focusing on user experience, automation, and enforcement:

1. **Smart Semantic Search** - Zero-config auto-index detection and file watching
2. **Reinforced TODO Enforcement** - Evidence-based verification ("Subagents LIE" protocol)
3. **Clean Output** - Concise agent status instead of verbose logging
4. **Delegation Enforcement** - 7-section mandatory parameters prevent bypassing agents
5. **New Quality Agents** - Momus (quality gate) and Comment-Checker

## Quick Summary

### What's Being Fixed

| Problem | Solution | Impact |
|---------|----------|--------|
| Users forget to create semantic index | Auto-prompt Y/N when missing | Zero-config experience |
| File watcher needs manual start | Auto-start when index exists | Seamless auto-updates |
| Watchers leak on Claude exit | atexit cleanup hook | No orphaned processes |
| Agents skip todos without evidence | Verification protocol with Read tool | Enforce actual completion |
| Verbose agent spawn output (500+ chars) | Clean format: `✓ agent:model → id` | Readable progress |
| Claude bypasses agents, uses Write directly | Mandatory delegation params | Force proper orchestration |
| Workers can spawn orchestrators | Agent type blocking | Prevent recursion |
| No quality gate validation | Momus agent | Catch issues before completion |
| Undocumented code | Comment-Checker agent | Maintain code quality |

### File Changes

**Modified (5 files):**
- `mcp_bridge/tools/semantic_search.py` - Auto-index + cleanup
- `mcp_bridge/hooks/todo_enforcer.py` - Verification protocol
- `mcp_bridge/tools/agent_manager.py` - Delegation + output
- `.claude/agents/stravinsky.md` - 7-section protocol
- `mcp_bridge/server.py` - Register new agents

**Created (6 files):**
- `.claude/agents/momus.md` - Quality gate agent
- `.claude/agents/comment_checker.md` - Doc validator
- `tests/test_semantic_auto_index.py` - Auto-index tests
- `tests/test_delegation_enforcement.py` - Delegation tests
- `stravinsky_improvements_20260116/spec.md` - This spec
- `stravinsky_improvements_20260116/plan.md` - Implementation plan

## Implementation Phases

### Phase 1: Smart Semantic Search (4-6h)
- Auto-detect missing index with Y/N prompt (30s timeout)
- Auto-start file watcher when index exists
- Register atexit cleanup for watchers
- Non-interactive fallback (return error in CI)

### Phase 2: TODO Enforcement (3-4h)
- Extract evidence (file paths, URLs) from output
- Verify file claims with Read tool
- Reject completions without evidence
- "Subagents LIE" verification protocol

### Phase 3: Clean Output (2-3h)
- Format: `✓ explore:gemini-3-flash → agent_a7246077`
- Progress: `⏳ agent_id running (15s)...`
- Complete: `✅ agent_id (42s) - Found 3 auth files`
- ANSI color coding (green/yellow/cyan/red)

### Phase 4: Delegation Enforcement (4-5h)
- Required: delegation_reason, expected_outcome, required_tools
- Optional: success_criteria, fallback_plan, forbidden_actions
- Agent type blocking (workers cannot spawn orchestrators/workers)
- Tool validation (check agent has access to required tools)

### Phase 5: New Agents (3-4h)
- Momus: Quality gate with validation checklist
- Comment-Checker: Find undocumented code, generate docs
- Tool registration and integration tests

## Success Criteria

**User Experience:**
- [ ] First-time user runs `semantic_search()` → prompted to create index
- [ ] Index auto-creates on "Y" → file watcher auto-starts
- [ ] Watcher survives Claude restarts, stops on Claude exit
- [ ] Agent spawn output under 100 chars: `✓ agent:model → id`
- [ ] Progress updates every 10s visible in stderr

**Enforcement:**
- [ ] Agents cannot complete todos without evidence (file:line format)
- [ ] Vague claims like "I created the file" rejected
- [ ] Workers blocked from spawning orchestrators/other workers
- [ ] agent_spawn fails fast with clear errors for missing params

**Quality:**
- [ ] Momus validates work before approval
- [ ] Comment-Checker finds functions without docstrings
- [ ] All tests pass (unit + integration)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Blocking prompt breaks CI | 30s timeout, non-interactive detection |
| Watcher crashes on startup | Try/except, log error, continue |
| Verification too strict | Allow `skip_verification: true` flag |
| Output mode breaks workflows | Default to verbose, opt-in to clean |

## Dependencies

**Requires (already installed):**
- chromadb >= 0.6.0
- watchdog ~= 5.0.0
- rich >= 13.0.0
- pathspec >= 0.12.0

**No new dependencies needed.**

## Testing Strategy

1. **Unit Tests:** Each helper function tested in isolation
2. **Integration Tests:** End-to-end workflows (auto-index, verification, delegation)
3. **Manual Verification:** Human testers validate each phase
4. **Regression Tests:** Ensure existing features still work

## Deployment

```bash
# 1. Implement all phases
# 2. Run tests
pytest tests/

# 3. Bump version
# pyproject.toml: version = "0.4.55"

# 4. Deploy
./deploy.sh

# 5. Clear uvx cache
python3 -c "import shutil; from pathlib import Path; shutil.rmtree(Path.home() / '.cache' / 'uv', ignore_errors=True)"

# 6. Restart Claude Code
```

## Documentation Updates

**Update:**
- `README.md` - Add semantic search auto-index section
- `ARCHITECTURE.md` - Document delegation enforcement
- `.claude/agents/stravinsky.md` - 7-section delegation protocol

**Create:**
- `docs/SEMANTIC_SEARCH.md` - User guide for semantic features
- `docs/DELEGATION_PROTOCOL.md` - Agent orchestration guide

## Related Issues

- Semantic search UX improvement (zero-config)
- TODO enforcement weakness (agents skip work)
- Verbose output readability
- Agent recursion prevention
- Quality validation before completion

## Next Steps

1. Review this plan with stakeholders
2. Set up feature branch: `feature/orchestration-improvements`
3. Implement Phase 1 (semantic search)
4. Manual verification after each phase
5. Merge to main after all phases complete + tests pass
