# Stravinsky Rollback - Quick Reference Guide

**For users and developers who need quick answers**

---

## 🎯 What Problem Does This Solve?

**Problem**: Stravinsky updates can fail, leaving your hooks/commands/settings in a broken state with no way to recover.

**Solution**: Automatic backup + atomic updates + automatic rollback = **updates are now safer than manual management**.

---

## 🚀 User Quick Start

### For End Users (No Code)

```bash
# Check backup status
stravinsky backup list

# See what happened during updates
stravinsky audit log --limit 10

# Rollback to previous version (if something breaks)
stravinsky rollback undo

# Rollback to specific version
stravinsky rollback to v0.3.8
```

### What Happens Automatically

1. **Before Update**: We backup all your hooks, commands, settings
2. **During Update**: New files downloaded to staging area
3. **After Update**: We verify everything works
4. **If Problem Detected**: Automatic rollback to previous version
5. **You Get Notified**: Full details of what happened

---

## 🔒 Safety Guarantees

| Guarantee | What It Means | How It Works |
|-----------|--------------|-------------|
| **No Data Loss** | Your modifications never deleted | Every file backed up before update |
| **Automatic Recovery** | If update fails, we fix it automatically | Post-update checks trigger auto-rollback |
| **Point-in-Time Recovery** | Restore any previous version | All versions kept for 2 years |
| **Atomic Updates** | Either fully works or fully reverts | No partial/broken states |
| **Full Audit Trail** | Every operation logged for debugging | Complete operation history available |

---

## 🛠️ For Developers

### Core Modules

```
mcp_bridge/rollback/
├── backup_manager.py        # Create/verify/restore backups
├── rollback_manager.py       # Execute manual/automatic rollbacks
├── recovery_manager.py       # Recover individual files/directories
├── validator.py              # Pre-update validation checks
├── audit_logger.py           # Operation logging & querying
├── transaction.py            # Atomic file operations
└── config.py                 # Configuration management
```

### Key Classes

```python
# Create backup
backup_mgr = BackupManager()
await backup_mgr.create_backup("v0.3.9")

# Validate before update
validator = PreUpdateValidator()
result = await validator.run_all_checks()

# Rollback if needed
rollback_mgr = RollbackManager(backup_mgr, validator, audit_logger)
await rollback_mgr.manual_rollback("v0.3.8")

# Query audit log
audit = AuditLogger()
events = await audit.query_events(event_type="UPDATE_FAILED")
```

---

## 📋 Complete Feature Matrix

| Feature | Status | Location |
|---------|--------|----------|
| **Backup Creation** | ✅ Designed | backup_manager.py |
| **Backup Verification** | ✅ Designed | backup_manager.py |
| **Pre-Update Validation** | ✅ Designed | validator.py |
| **Atomic Updates** | ✅ Designed | transaction.py |
| **Auto-Rollback** | ✅ Designed | rollback_manager.py |
| **Manual Rollback** | ✅ Designed | rollback_manager.py |
| **Single-File Recovery** | ✅ Designed | recovery_manager.py |
| **Directory Recovery** | ✅ Designed | recovery_manager.py |
| **Audit Logging** | ✅ Designed | audit_logger.py |
| **CLI Commands** | ✅ Designed | cli/rollback_cli.py |
| **Configuration** | ✅ Designed | config.py |
| **Error Detection Matrix** | ✅ Designed | validator.py |
| **Three-Level Recovery** | ✅ Designed | recovery_manager.py |
| **Chaos Testing** | ✅ Designed | tests/rollback/ |

---

## 🔍 Architecture at a Glance

```
UPDATE FLOW:
  ┌─ Pre-Update Checks (validator) ──────────────┐
  │  • Disk space sufficient?                     │
  │  • File permissions OK?                       │
  │  • No files locked?                           │
  │  • Hooks/commands/settings valid?             │
  └──────────────────────────────────────────────┘
                       ↓
  ┌─ Create Backup (backup_manager) ─────────────┐
  │  • Copy hooks, commands, settings             │
  │  • Compute SHA256 checksums                   │
  │  • Create tar.gz archives                     │
  │  • Generate manifest.json                     │
  │  • Verify archive integrity                   │
  └──────────────────────────────────────────────┘
                       ↓
  ┌─ Apply Update (atomic_swap) ──────────────────┐
  │  • Write new files to staging                 │
  │  • Atomic rename: old→old.bak, new→target    │
  │  • Update version pointers                    │
  └──────────────────────────────────────────────┘
                       ↓
  ┌─ Verify Update (validator) ───────────────────┐
  │  • All files present?                         │
  │  • Checksums match?                           │
  │  • Hooks/commands/settings parse?             │
  └──────────────────────────────────────────────┘
           ↓ (FAIL) or ↓ (SUCCESS)
           │                    │
     AUTO-ROLLBACK          ✅ UPDATE COMPLETE
     • Restore from backup
     • Verify restoration
     • Log failure
```

---

## 📊 Backup Storage Layout

```
~/.stravinsky/rollback/
├── backups/
│   ├── v0.3.8/
│   │   ├── hooks.tar.gz        (global + project hooks)
│   │   ├── commands.tar.gz      (global + project commands)
│   │   ├── settings.json        (merged settings)
│   │   └── manifest.json        (checksums + metadata)
│   └── v0.3.9/
│       └── ...
├── audit/
│   ├── operations.log           (immutable append-only)
│   └── audit.db                 (SQLite for querying)
├── recovery/
│   └── staging/                 (temp work area)
└── config.json                  (rollback settings)
```

**Space**: ~50-500 MB total (10 versions × 5-50 MB each)

---

## 🎯 Error Handling Matrix

| Error | Detection | Auto-Rollback | User Action |
|-------|-----------|---------------|------------|
| Parse error (hooks/commands) | Syntax validation | ✅ Yes | None needed |
| Schema error (settings) | Schema validation | ✅ Yes | None needed |
| Permission denied | File access test | ❌ No | Fix permissions |
| Disk full | Space check | ✅ Yes | Free disk space |
| Corrupted backup | Checksum failure | ❌ No | Use older backup |
| File locked | fcntl check | ❌ No | Close app using file |
| Dependency missing | Import test | ✅ Yes | None needed |
| Unknown error | Exception catch | ✅ Yes | None needed |

---

## 🔐 Safety Checklist

Before ANY update:

- [ ] Disk space check (need 2x backup size)
- [ ] File permissions verified
- [ ] No files locked
- [ ] Hooks syntax valid
- [ ] Commands parse correctly
- [ ] Settings schema compliant
- [ ] Previous backups intact
- [ ] Backup capacity available

---

## 📈 Metrics & Monitoring

### What We Track

```
• Update success/failure rate
• Rollback frequency
• Average recovery time
• Backup creation time
• Verification time
• Disk space usage
• Audit log size
```

### Example Queries

```python
# Show failed updates in last 24 hours
await audit.query_events(
    event_type="UPDATE_FAILED",
    start_date=datetime.utcnow() - timedelta(days=1)
)

# Show rollbacks by version
await audit.query_events(
    event_type="MANUAL_ROLLBACK"
)

# Show update duration statistics
events = await audit.query_events(
    event_type="UPDATE_SUCCESS"
)
durations = [e["duration_seconds"] for e in events]
# Calculate avg, min, max, percentiles
```

---

## 🚨 Emergency Procedures

### If Update Completely Fails

```bash
# 1. See what happened
stravinsky audit log --limit 5

# 2. Rollback to previous version
stravinsky rollback undo

# 3. If that doesn't work, list all versions
stravinsky backup list

# 4. Rollback to specific version
stravinsky rollback to v0.3.7
```

### If All Backups Corrupted

```bash
# Show recovery guide
stravinsky recovery emergency

# Manual recovery steps provided
```

### If Rollback Itself Fails (CRITICAL)

```
⚠️ CRITICAL ERROR: Automatic rollback failed
→ Check ~/.stravinsky/rollback/audit/operations.log for details
→ Run: stravinsky recovery emergency
→ Follow manual recovery procedures in RECOVERY_GUIDE.md
```

---

## 📚 Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| **ROLLBACK_ARCHITECTURE.md** | Complete technical specification | Architects, Developers |
| **ROLLBACK_IMPLEMENTATION_GUIDE.md** | Step-by-step implementation | Developers |
| **ROLLBACK_QUICK_REFERENCE.md** | Quick answers (this file) | Everyone |
| **RECOVERY_GUIDE.md** | How to recover from any failure | Users, Support |

---

## 🔗 Related Commands

```bash
# Authentication
stravinsky-auth login gemini
stravinsky-auth login openai

# Sessions & Audit
stravinsky-sessions                    # Session history
stravinsky audit log                   # Operation history

# Backups
stravinsky backup list                 # See all backups
stravinsky backup show v0.3.8
stravinsky backup verify v0.3.8

# Rollback
stravinsky rollback list               # Available versions
stravinsky rollback undo               # Revert to previous
stravinsky rollback to v0.3.8          # Revert to specific

# Recovery
stravinsky recovery file <path>        # Recover one file
stravinsky recovery directory <dir>    # Recover directory
stravinsky recovery version v0.3.8     # Recover full version
stravinsky recovery emergency          # Emergency guide
```

---

## ✅ Phase Implementation Status

### Phase 1: Core Backup System ⏳ TODO
- Backup creation/verification
- Pre-update validation
- Audit infrastructure

### Phase 2: Atomic Updates ⏳ TODO
- Transaction logging
- Atomic file operations
- Post-update verification
- Auto-rollback triggers

### Phase 3: Recovery & Resilience ⏳ TODO
- Three-level recovery
- Emergency procedures
- Chaos testing

### Phase 4: Configuration & Monitoring ⏳ TODO
- Settings system
- Audit querying
- Monitoring/alerting

### Phase 5: Testing & Hardening ⏳ TODO
- Comprehensive test suite
- Edge case handling
- Performance optimization

---

## 🤔 FAQ

### Q: Will updates be slower?
**A**: No. Backups happen once per update (~500ms-2s). Updates are same speed.

### Q: How much disk space do I need?
**A**: ~500 MB for 10 versions. Configurable via `config.json`.

### Q: Can I disable auto-rollback?
**A**: Yes, via `config.json`: `"auto_rollback_on_failure": false`

### Q: How long are backups kept?
**A**: 2 years by default, configurable in `config.json`.

### Q: Can I recover deleted files?
**A**: Yes, with `stravinsky recovery file <path> <version>`

### Q: What if something goes wrong during rollback?
**A**: Complete audit trail logged. Run `stravinsky recovery emergency` for manual recovery steps.

### Q: Is there a performance overhead?
**A**: Minimal (~1-2s per update for backup creation). Verification adds ~500ms-1s.

### Q: Can I test rollback without breaking my setup?
**A**: Not yet, but chaos testing framework is in Phase 5.

---

## 🎓 Key Concepts

**Atomic**: Either fully succeeds or fully fails. No partial/broken states.

**Backup**: Complete copy of hooks, commands, settings at a point in time.

**Manifest**: Metadata file listing all files in backup with checksums.

**Rollback**: Revert to a previous version (manual or automatic).

**Recovery**: Restore deleted/corrupted files from backup.

**Checksum**: SHA256 hash verifying file integrity.

**Audit Trail**: Immutable log of all operations for debugging.

**Transaction Log**: Records each file operation during update.

**Point-in-Time Recovery**: Ability to restore any previous version.

---

## 📞 Getting Help

1. **Check the audit log**: `stravinsky audit log --limit 20`
2. **Review recovery guide**: `stravinsky recovery emergency`
3. **Read full architecture**: ROLLBACK_ARCHITECTURE.md
4. **Check implementation**: ROLLBACK_IMPLEMENTATION_GUIDE.md

---

**Last Updated**: 2026-01-08
**Version**: 1.0
**Status**: Strategic Design Complete ✅
