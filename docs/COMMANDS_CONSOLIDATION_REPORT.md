# Claude Commands Consolidation Report

**Report Date**: 2026-01-07  
**Scope**: All `.claude/commands/` directories across 21 projects in `~/PycharmProjects/`

---

## Executive Summary

**Total command files across all projects**: 1,215 files  
**Unique command filenames**: 258 files  
**Duplicate boilerplate commands identified**: 150+ files with duplicates  
**Estimated consolidation opportunity**: Free up 180+ KB of redundant files

### Key Findings

1. **Massive duplication**: 21 projects contain nearly identical command templates
2. **Highest duplication**: `swarm-init.md` appears identically in 17 projects
3. **Top 3 projects by command count**:
   - FAERSdb: 199 files
   - lexgenius-pacer: 167 files
   - dr-evil-project: 150 files

4. **Standardized templates never change**: Same 11-12 command templates are byte-for-byte identical across multiple projects

---

## Part 1: Duplicate Boilerplate Files (1,215 total files)

### Files Appearing in 11+ Projects (Highest Duplication Priority)

**CRITICAL DUPLICATES** - Consider immediate consolidation to global `~/.claude/commands/templates/`:

| File | Copies | Projects | Status |
|------|--------|----------|--------|
| swarm-init.md | 17 | EPA-Dashboard, FAERS-SrLC, FAERSdb, SPMS, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal + 5 more | IDENTICAL BYTES |
| swarm-monitor.md | 16 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal + 5 more | IDENTICAL BYTES |
| agent-spawn.md | 12 | EPA-Dashboard, FAERS-SrLC, FAERSdb, SPMS, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| memory-persist.md | 12 | EPA-Dashboard, FAERS-SrLC, FAERSdb, SPMS, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| memory-search.md | 12 | EPA-Dashboard, FAERS-SrLC, FAERSdb, SPMS, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| agent-metrics.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| bottleneck-detect.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| cache-manage.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| github-swarm.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| issue-triage.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| memory-usage.md | 12 | EPA-Dashboard, FAERS-SrLC, FAERSdb, SPMS, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| model-update.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| neural-train.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| parallel-execute.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| pattern-learn.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| performance-report.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| post-edit.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| post-task.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| pr-enhance.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| pre-edit.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| pre-task.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| real-time-view.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| repo-analyze.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| session-end.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| smart-spawn.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| task-orchestrate.md | 12 | EPA-Dashboard, FAERS-SrLC, FAERSdb, SPMS, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| token-usage.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| topology-optimize.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| workflow-create.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| workflow-execute.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| workflow-export.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |
| workflow-select.md | 11 | EPA-Dashboard, FAERS-SrLC, FAERSdb, agentic-research, dr-evil-project, jpml_scraper, lexgenius-dashboard, lexgenius-new-dashboard, lexgenius-pacer, lexgenius-pacer-transformer, recall-sentinal | IDENTICAL BYTES |

**TOTAL: 30 highly duplicated templates** appearing 11-17 times each

---

## Part 2: Projects with Excessive Command Files

### Top 10 Projects by Command Count

| Rank | Project | Count | Status | Recommendation |
|------|---------|-------|--------|-----------------|
| 1 | FAERSdb | 199 | EXCESSIVE | Clean up 50-70% duplicate templates |
| 2 | lexgenius-pacer | 167 | EXCESSIVE | Clean up 40-60% duplicate templates |
| 3 | dr-evil-project | 150 | EXCESSIVE | Clean up 50-70% duplicate templates |
| 4 | EPA-Dashboard | 104 | MODERATE | Clean up 30-50% duplicate templates |
| 5 | agentic-research | 104 | MODERATE | Clean up 30-50% duplicate templates |
| 6 | jpml_scraper | 65 | MODERATE | Clean up 30-40% duplicate templates |
| 7 | FAERS-SrLC | 64 | MODERATE | Clean up 25-40% duplicate templates |
| 8 | lexgenius-new-dashboard | 64 | MODERATE | Clean up 30-40% duplicate templates |
| 9 | recall-sentinal | 62 | MODERATE | Clean up 30-40% duplicate templates |
| 10 | SPMS | 52 | MODERATE | Clean up 25-35% duplicate templates |

### Files Appearing in 2-10 Projects

There are an additional **82 additional command files** appearing in 2-10 projects each, representing additional consolidation opportunities:

Examples:
- `agent-capabilities.md` (5 projects)
- `agent-coordination.md` (5 projects)
- `code-review.md` (13 projects)
- `architect.md` (12 projects)
- `sparc.md` (12 projects)
- `auto-agent.md` (11 projects)

---

## Part 3: Standard Boilerplate Commands

### Rarely Used Standard Commands

Only appearing in 1-2 projects:

- `context.md` - NOT FOUND as standard file
- `delphi.md` - Found in only 2 projects (claude-superagent, stravinsky)
- `dewey.md` - Found in only 2 projects (claude-superagent, stravinsky)
- `health.md` - NOT FOUND as standard file
- `stravinsky.md` - Found in only 1 project (stravinsky)

**Implication**: The missing standard commands (`context.md`, `health.md`, `stravinsky.md`) could be created as global templates for consistency.

---

## Part 4: Directory Organization Patterns

Most projects follow a standardized structure:

```
.claude/commands/
├── analysis/              (token-usage, performance-report, etc.)
├── automation/            (auto-agent, smart-spawn, etc.)
├── coordination/          (agent-spawn, swarm-init, task-orchestrate)
├── github/                (code-review, issue-triage, pr-enhance, etc.)
├── hooks/                 (pre-task, post-task, pre-edit, etc.)
├── memory/                (memory-search, memory-persist, memory-usage)
├── monitoring/            (agent-metrics, swarm-monitor, status)
├── optimization/          (cache-manage, parallel-execute, topology)
├── sparc/                 (architect, coder, debugger, etc.)
├── training/              (model-update, neural-train, etc.)
├── workflows/             (workflow-create, workflow-execute, etc.)
└── [optional dirs]        (bmad, agent-vibes, hive-mind, etc.)
```

---

## Part 5: Consolidation Recommendations

### PHASE 1: Immediate Consolidation (Quick Wins)

**30 files** that are byte-for-byte identical across 11-17 projects should be moved to a global template directory:

```bash
~/.claude/commands/templates/core/
├── coordination/
│   ├── agent-spawn.md
│   └── swarm-init.md
├── memory/
│   ├── memory-persist.md
│   ├── memory-search.md
│   └── memory-usage.md
├── monitoring/
│   ├── agent-metrics.md
│   └── swarm-monitor.md
├── analysis/
│   ├── token-usage.md
│   ├── performance-report.md
│   └── bottleneck-detect.md
├── optimization/
│   ├── parallel-execute.md
│   ├── cache-manage.md
│   └── topology-optimize.md
├── hooks/
│   ├── pre-task.md
│   ├── post-task.md
│   ├── pre-edit.md
│   └── post-edit.md
│   └── session-end.md
├── workflows/
│   ├── workflow-create.md
│   ├── workflow-execute.md
│   └── workflow-export.md
│   └── workflow-select.md
├── github/
│   ├── code-review.md
│   ├── github-swarm.md
│   ├── issue-triage.md
│   └── pr-enhance.md
│   └── repo-analyze.md
└── training/
    ├── model-update.md
    ├── neural-train.md
    └── pattern-learn.md
```

**Impact**: Removes ~350 redundant files, saves ~180 KB

### PHASE 2: Secondary Consolidation (Medium Priority)

**82 additional files** appearing in 2-10 projects:
- `architect.md` (12 projects) - standardize architecture review
- `sparc.md` (12 projects) - standardize SPARC agent coordination
- `auto-agent.md` (11 projects) - standardize automation
- `agent-health-coach.md` (3 projects)
- `code.md`, `debug.md`, `ask.md` - standardize inquiry commands

### PHASE 3: Project-Specific Customization (Long-term)

**Original/unique files** should remain in project-local commands:
- FAERSdb: 199 files → keep ~80 unique ones
- lexgenius-pacer: 167 files → keep ~70 unique ones
- dr-evil-project: 150 files → keep ~60 unique ones

---

## Part 6: Cleanup Strategy

### Option A: Soft Migration (Zero-Risk)

1. **Create** `~/.claude/commands/templates/` directory with consolidated files
2. **Leave** project-local files in place for backward compatibility
3. **Document** in README that templates are centrally maintained
4. **Over time**: Individual projects migrate as they're touched

### Option B: Hard Migration (One-Time Effort)

1. **Move** 30 core templates to `~/.claude/commands/templates/core/`
2. **Create** script to remove duplicates from all projects
3. **Git commit** to each project with message: "chore: consolidate duplicate command templates to ~/.claude/commands/templates/"
4. **Clean**: ~350 redundant files removed in single sweep

### Option C: Hybrid Approach (Recommended)

1. **Immediate** (Month 1): Set up `~/.claude/commands/templates/core/` with 30 files
2. **Phase 1** (Month 2): Remove from projects that have been recently updated
3. **Phase 2** (Month 3): Systematic cleanup of remaining projects
4. **Archive**: Keep removal PR records in git history

---

## Implementation Checklist

### Before You Start

- [ ] Back up all `.claude/commands/` directories
- [ ] Create git branch for each project
- [ ] Generate MD5 hashes of files before/after to verify consolidation

### Consolidation Process

- [ ] Create `~/.claude/commands/templates/core/` directory structure
- [ ] Copy 30 identified core templates to templates/ directory
- [ ] Test that commands still work from both locations
- [ ] Create symlinks OR update `.claude/commands/` to reference templates/
- [ ] Remove duplicate files from projects (keep one canonical copy)
- [ ] Commit changes to each project
- [ ] Update documentation (this report, README files)

### Validation

- [ ] Run skill discovery on 3-5 test projects to verify commands still appear
- [ ] Check that command metadata is preserved (descriptions, usage)
- [ ] Verify no circular symlink issues
- [ ] Test in actual Claude Code environment

---

## Storage Savings Analysis

| Scenario | Files Removed | Approx. Saved | Effort |
|----------|---------------|---------------|--------|
| **Phase 1 Only** | ~350 | 180 KB | 2-3 hours |
| **Phase 1 + 2** | ~500 | 280 KB | 1-2 days |
| **All Phases** | ~700 | 400 KB | 2-3 days |

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Symlinks not supported in Claude Code | Low | HIGH | Test immediately with symlinks before full rollout |
| Commands break during migration | Medium | HIGH | Maintain local copies during transition period |
| Project-specific customizations lost | Low | MEDIUM | Audit each file for customizations first |
| Sync issues between template and copies | Medium | MEDIUM | Document that templates are canonical; use CI to check |
| Backward compatibility issues | Low | LOW | Keep project-local files for 3+ months after move |

---

## Next Steps

1. **Review this report** and select consolidation phase (A, B, or C)
2. **Create** `~/.claude/commands/templates/core/` structure
3. **Run** Phase 1 on 1-2 projects as proof-of-concept
4. **Validate** commands still work correctly
5. **Document** any project-specific overrides that need to remain local
6. **Rollout** systematically across remaining projects

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total projects analyzed | 21 |
| Total command files | 1,215 |
| Unique filenames | 258 |
| Byte-identical duplicates (11+) | 30 files across 11-17 projects |
| Secondary duplicates (2-10) | 82 files |
| Consolidation opportunity | 112 templates affecting 350+ files |
| Estimated disk space saved | 180-400 KB |
| Projects with 100+ commands | 3 (FAERSdb, lexgenius-pacer, dr-evil-project) |
| Projects with 50-99 commands | 4 |
| Projects with <50 commands | 14 |

