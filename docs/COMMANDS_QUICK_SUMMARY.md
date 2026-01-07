# Claude Commands Consolidation - Quick Summary

**Report**: `/Users/davidandrews/PycharmProjects/stravinsky/docs/COMMANDS_CONSOLIDATION_REPORT.md`

## The Problem

- 1,215 command files across 21 projects
- 30 files appear byte-for-byte identical in 11-17 projects each
- 3 projects have 150+ commands (FAERSdb, lexgenius-pacer, dr-evil-project)
- Same templates duplicated across every project

## The Opportunity

**Move 30 identical templates to `~/.claude/commands/templates/core/`**

Results:
- Remove ~350 redundant files
- Save ~180 KB of disk space
- Standardize command discovery across all projects
- Enable single-point-of-truth for core commands

## Most Duplicated (11-17 copies each)

| File | Copies | Priority |
|------|--------|----------|
| swarm-init.md | 17 | CRITICAL |
| swarm-monitor.md | 16 | CRITICAL |
| agent-spawn.md | 12 | CRITICAL |
| memory-persist.md | 12 | CRITICAL |
| memory-search.md | 12 | CRITICAL |
| memory-usage.md | 12 | CRITICAL |
| task-orchestrate.md | 12 | CRITICAL |
| agent-metrics.md | 11 | HIGH |
| bottleneck-detect.md | 11 | HIGH |
| cache-manage.md | 11 | HIGH |
| github-swarm.md | 11 | HIGH |
| issue-triage.md | 11 | HIGH |
| model-update.md | 11 | HIGH |
| neural-train.md | 11 | HIGH |
| parallel-execute.md | 11 | HIGH |
| pattern-learn.md | 11 | HIGH |
| performance-report.md | 11 | HIGH |
| post-edit.md | 11 | HIGH |
| post-task.md | 11 | HIGH |
| pr-enhance.md | 11 | HIGH |
| pre-edit.md | 11 | HIGH |
| pre-task.md | 11 | HIGH |
| real-time-view.md | 11 | HIGH |
| repo-analyze.md | 11 | HIGH |
| session-end.md | 11 | HIGH |
| smart-spawn.md | 11 | HIGH |
| token-usage.md | 11 | HIGH |
| topology-optimize.md | 11 | HIGH |
| workflow-create.md | 11 | HIGH |
| workflow-execute.md | 11 | HIGH |
| workflow-export.md | 11 | HIGH |
| workflow-select.md | 11 | HIGH |

## Projects Needing Cleanup

| Project | Commands | Cleanup % |
|---------|----------|-----------|
| FAERSdb | 199 | 50-70% |
| lexgenius-pacer | 167 | 40-60% |
| dr-evil-project | 150 | 50-70% |
| EPA-Dashboard | 104 | 30-50% |
| agentic-research | 104 | 30-50% |

## Implementation Steps

### Phase 1 (Quick): Create Global Templates
```bash
mkdir -p ~/.claude/commands/templates/core/{coordination,memory,monitoring,analysis,optimization,hooks,workflows,github,training}
# Copy 30 identical files to templates/
```

### Phase 2 (Medium): Remove from Projects
```bash
# For each project:
cd ~/PycharmProjects/{project}
rm -f .claude/commands/coordination/agent-spawn.md
# ... remove all 30 duplicates
```

### Phase 3 (Optional): Link or Reference
- Option A: Keep project-local copies (zero risk)
- Option B: Create symlinks to templates/
- Option C: Update skill discovery to check templates/

## Risk Level: LOW

- No changes required to actual command content
- Commands remain discoverable by Claude
- Can rollback by restoring deleted files from git
- Test on 1-2 projects first

## Time Estimate

- Phase 1 only: 2-3 hours
- Phase 1 + 2: 1-2 days
- Full implementation: 2-3 days

## Next Actions

1. Review full report: COMMANDS_CONSOLIDATION_REPORT.md
2. Decide on migration strategy (A, B, or C)
3. Create `~/.claude/commands/templates/core/` directory
4. Copy 30 core templates there
5. Test on stravinsky project first
6. Roll out to other projects

---

See full analysis in: `COMMANDS_CONSOLIDATION_REPORT.md`
