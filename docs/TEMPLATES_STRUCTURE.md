# Global Templates Directory Structure

## Recommended Layout

Create this structure in `~/.claude/commands/templates/`:

```
~/.claude/commands/templates/
├── README.md                          # Usage guide
├── core/                              # Core templates (11-17 copies each)
│   ├── analysis/
│   │   ├── bottleneck-detect.md      # 11 projects
│   │   ├── performance-report.md     # 11 projects
│   │   └── token-usage.md            # 11 projects
│   ├── coordination/
│   │   ├── agent-spawn.md            # 12 projects
│   │   └── swarm-init.md             # 17 projects (HIGHEST)
│   ├── github/
│   │   ├── code-review.md            # 13 projects
│   │   ├── github-swarm.md           # 11 projects
│   │   ├── issue-triage.md           # 11 projects
│   │   ├── pr-enhance.md             # 11 projects
│   │   └── repo-analyze.md           # 11 projects
│   ├── hooks/
│   │   ├── post-edit.md              # 11 projects
│   │   ├── post-task.md              # 11 projects
│   │   ├── pre-edit.md               # 11 projects
│   │   ├── pre-task.md               # 11 projects
│   │   └── session-end.md            # 11 projects
│   ├── memory/
│   │   ├── memory-persist.md         # 12 projects
│   │   ├── memory-search.md          # 12 projects
│   │   └── memory-usage.md           # 12 projects
│   ├── monitoring/
│   │   ├── agent-metrics.md          # 11 projects
│   │   └── swarm-monitor.md          # 16 projects
│   ├── optimization/
│   │   ├── cache-manage.md           # 11 projects
│   │   ├── parallel-execute.md       # 11 projects
│   │   └── topology-optimize.md      # 11 projects
│   ├── training/
│   │   ├── model-update.md           # 11 projects
│   │   ├── neural-train.md           # 11 projects
│   │   └── pattern-learn.md          # 11 projects
│   └── workflows/
│       ├── workflow-create.md        # 11 projects
│       ├── workflow-execute.md       # 11 projects
│       ├── workflow-export.md        # 11 projects
│       ├── workflow-select.md        # 11 projects
│       └── task-orchestrate.md       # 12 projects
└── secondary/                         # Secondary templates (6-10 copies)
    ├── agents/
    │   ├── architect.md              # 12 projects
    │   ├── analyzer.md               # 5 projects
    │   ├── coder.md                  # 5 projects
    │   ├── debugger.md               # 5 projects
    │   └── reviewer.md               # 5 projects
    ├── automation/
    │   ├── auto-agent.md             # 11 projects
    │   └── smart-spawn.md            # 11 projects
    ├── orchestration/
    │   └── sparc.md                  # 12 projects
    └── real-time/
        └── real-time-view.md         # 11 projects
```

## File Distribution

**Core Templates (Phase 1 - IMMEDIATE)**
- 30 files, 11-17 copies each
- Total impact: 350 redundant files
- Savings: ~180 KB

**Secondary Templates (Phase 2 - OPTIONAL)**
- 8+ files, 6-10 copies each
- Total impact: 50+ redundant files
- Savings: ~30 KB

## Creation Instructions

### Step 1: Create Directory Structure
```bash
mkdir -p ~/.claude/commands/templates/core/{analysis,coordination,github,hooks,memory,monitoring,optimization,training,workflows}
mkdir -p ~/.claude/commands/templates/secondary/{agents,automation,orchestration,real-time}
```

### Step 2: Copy Core Templates
```bash
# From each project, copy to templates/
# Example for swarm-init.md (appears in 17 projects):

# Source: EPA-Dashboard/.claude/commands/coordination/swarm-init.md
cp ~/PycharmProjects/EPA-Dashboard/.claude/commands/coordination/swarm-init.md \
   ~/.claude/commands/templates/core/coordination/swarm-init.md

# Verify it's correct
md5 ~/.claude/commands/templates/core/coordination/swarm-init.md
# Should match all 17 copies
```

### Step 3: Create README
Create `~/.claude/commands/templates/README.md`:

```markdown
# Claude Commands Global Templates

This directory contains command templates that are duplicated across multiple projects.

## Usage

Claude's skill discovery automatically includes:
1. Project-local `.claude/commands/` files
2. User-global `~/.claude/commands/` files
3. This `templates/` directory

Commands in `templates/` will be discovered in all projects unless overridden locally.

## Structure

- `core/` - High-priority templates (11-17 copies across projects)
- `secondary/` - Additional templates (6-10 copies across projects)

## Consolidation Status

- Total templates: 38
- Projects using these templates: 21
- Estimated files removed: 350+
- Disk space saved: ~180 KB

See: `~/PycharmProjects/stravinsky/docs/COMMANDS_CONSOLIDATION_REPORT.md`
```

## Verification Checklist

- [ ] All 30 core files copied to templates/core/
- [ ] MD5 hashes match original files (byte-for-byte identical)
- [ ] No circular symlinks or path issues
- [ ] Test skill discovery in Claude Code (should see commands from both locations)
- [ ] Verify no command name conflicts
- [ ] Documentation updated

## Phase 1 vs Phase 2

### Phase 1 (RECOMMENDED FIRST)
- 30 core files (11-17 copies)
- Create `~/.claude/commands/templates/core/`
- Remove from all projects
- Impact: 350 files removed, 180 KB saved
- Risk: LOW
- Effort: 2-3 hours

### Phase 2 (OPTIONAL LATER)
- 8+ secondary files (6-10 copies)
- Create `~/.claude/commands/templates/secondary/`
- Remove from projects
- Impact: 50+ additional files removed, 30 KB saved
- Risk: MEDIUM
- Effort: 4-6 hours

## Rollback Plan

If anything breaks:

```bash
# Git restore from each project
cd ~/PycharmProjects/{project}
git restore .claude/commands/
```

All deleted files are in git history and can be restored.
