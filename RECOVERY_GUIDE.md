# Stravinsky Recovery Guide

**For when things go wrong - step-by-step recovery procedures**

**Version**: 1.0
**Last Updated**: 2026-01-08

---

## Table of Contents

1. [Level 1 Recovery](#level-1-recovery-single-file) - Recover one file
2. [Level 2 Recovery](#level-2-recovery-directory) - Recover entire directory
3. [Level 3 Recovery](#level-3-recovery-full-version) - Full version rollback
4. [Emergency Procedures](#emergency-procedures) - When normal recovery fails
5. [Troubleshooting](#troubleshooting) - Common issues and solutions

---

## 🆘 Quick Triage

**Problem → Solution**:

- **"Single file got corrupted"** → [Level 1 Recovery](#level-1-recovery-single-file)
- **"All hooks disappeared"** → [Level 2 Recovery](#level-2-recovery-directory)
- **"Update broke everything"** → [Level 3 Recovery](#level-3-recovery-full-version)
- **"Rollback itself failed"** → [Emergency Procedures](#emergency-procedures)
- **"Nothing is working"** → [Call Emergency Recovery](#emergency-recovery)

---

## Level 1 Recovery: Single File

**Use when**: One specific file is corrupted or missing

### Quick Fix (Preferred)

```bash
# Replace ~/.claude/hooks/custom.md from backup
stravinsky recovery file ~/.claude/hooks/custom.md

# Or specify which version to restore from
stravinsky recovery file ~/.claude/hooks/custom.md v0.3.8
```

**Expected output**:
```
✅ File recovered: ~/.claude/hooks/custom.md
   Source: backup v0.3.9 (2026-01-08T15:34:22Z)
   Restored 1,234 bytes
```

### Manual Recovery (If CLI Doesn't Work)

```bash
# 1. List available backups
ls ~/.stravinsky/rollback/backups/

# Example output:
# v0.3.7  v0.3.8  v0.3.9

# 2. Find which backup contains your file
tar tzf ~/.stravinsky/rollback/backups/v0.3.9/hooks.tar.gz | \
  grep "custom.md"

# Example output:
# hooks/global/custom.md

# 3. Extract the specific file
tar xzf ~/.stravinsky/rollback/backups/v0.3.9/hooks.tar.gz \
  -C ~/.claude/ hooks/global/custom.md

# 4. Verify the file
ls -la ~/.claude/hooks/custom.md
```

### Verification

After recovery, verify the file:

```bash
# Check file content
cat ~/.claude/hooks/custom.md | head -20

# Check file size
ls -lh ~/.claude/hooks/custom.md

# Check timestamp
stat ~/.claude/hooks/custom.md
```

---

## Level 2 Recovery: Directory

**Use when**: Entire directory corrupted/missing (hooks, commands, settings)

### Quick Fix (Preferred)

```bash
# Restore entire hooks directory
stravinsky recovery directory ~/.claude/hooks

# Or from specific version
stravinsky recovery directory ~/.claude/hooks v0.3.8
```

**Expected output**:
```
✅ Directory recovered: ~/.claude/hooks
   Source: backup v0.3.9 (2026-01-08T15:34:22Z)
   Restored 5 files, 45 KB
```

### Manual Recovery (If CLI Doesn't Work)

```bash
# 1. Backup current broken directory (if exists)
if [ -d ~/.claude/hooks ]; then
  mv ~/.claude/hooks ~/.claude/hooks.broken.$(date +%s)
fi

# 2. Create fresh directory
mkdir -p ~/.claude/hooks

# 3. Extract from backup
tar xzf ~/.stravinsky/rollback/backups/v0.3.9/hooks.tar.gz \
  -C ~/.claude/

# 4. Verify recovery
ls -la ~/.claude/hooks/
```

### Multi-Directory Recovery

```bash
# Recover all directories from specific version
for dir in hooks commands; do
  mkdir -p ~/.claude/$dir
  tar xzf ~/.stravinsky/rollback/backups/v0.3.8/$dir.tar.gz \
    -C ~/.claude/
done

# Recover settings
cp ~/.stravinsky/rollback/backups/v0.3.8/settings.json \
   ~/.claude/settings.json
```

### Verification

After recovery, verify all files present:

```bash
# Count files
find ~/.claude/hooks -type f | wc -l

# Check syntax of Markdown files
for f in ~/.claude/hooks/*.md; do
  echo "Checking $f..."
  # Try to parse (if you have a hook validator)
done

# Check settings are valid JSON
cat ~/.claude/settings.json | python3 -m json.tool > /dev/null && echo "✅ Valid JSON"
```

---

## Level 3 Recovery: Full Version Rollback

**Use when**: Entire package/version broken, need to revert to previous state

### Quick Rollback (Preferred)

```bash
# Rollback to previous version (before current broken update)
stravinsky rollback undo

# Or rollback to specific version
stravinsky rollback to v0.3.8
```

**Expected output**:
```
✅ Rollback successful!
   From: v0.3.9
   To:   v0.3.8
   Created backup: v0.3.9.pre_rollback
   Duration: 12.3 seconds
```

### Manual Rollback (If CLI Doesn't Work)

```bash
# 1. See available versions
ls -la ~/.stravinsky/rollback/backups/

# 2. Identify target version (usually most recent before failure)
# Example: v0.3.8 is the version before current broken v0.3.9

# 3. Create backup of current broken state
BACKUP_DIR="$HOME/.stravinsky/rollback/backups"
BROKEN_VERSION=$(cat $BACKUP_DIR/latest.json | jq -r '.version')

tar czf "$BACKUP_DIR/${BROKEN_VERSION}.pre_rollback.tar.gz" \
  ~/.claude/hooks \
  ~/.claude/commands \
  ~/.claude/settings.json 2>/dev/null || true

# 4. Restore from target version
TARGET_VERSION="v0.3.8"

# Hooks
tar xzf "$BACKUP_DIR/$TARGET_VERSION/hooks.tar.gz" -C ~/.

# Commands
tar xzf "$BACKUP_DIR/$TARGET_VERSION/commands.tar.gz" -C ~/.

# Settings
cp "$BACKUP_DIR/$TARGET_VERSION/settings.json" ~/.claude/settings.json

# 5. Update version pointer
echo "{\"version\": \"$TARGET_VERSION\"}" > "$BACKUP_DIR/latest.json"
```

### Complete Rollback Script

```bash
#!/bin/bash
set -e

TARGET_VERSION="${1:-v0.3.8}"
BACKUP_DIR="$HOME/.stravinsky/rollback/backups"

echo "🔄 Rolling back to $TARGET_VERSION..."

# Verify backup exists
if [ ! -d "$BACKUP_DIR/$TARGET_VERSION" ]; then
  echo "❌ Backup not found: $TARGET_VERSION"
  echo "Available versions:"
  ls "$BACKUP_DIR"
  exit 1
fi

# Create backup of current state
CURRENT=$(cat "$BACKUP_DIR/latest.json" 2>/dev/null | jq -r '.version' || echo "unknown")
echo "📦 Backing up current state ($CURRENT)..."

mkdir -p "$BACKUP_DIR/staging"
tar czf "$BACKUP_DIR/${CURRENT}.pre_rollback.tar.gz" \
  -C "$HOME" .claude 2>/dev/null || true

# Restore from target
echo "♻️  Restoring from $TARGET_VERSION..."

tar xzf "$BACKUP_DIR/$TARGET_VERSION/hooks.tar.gz" -C ~/.
tar xzf "$BACKUP_DIR/$TARGET_VERSION/commands.tar.gz" -C ~/.
[ -f "$BACKUP_DIR/$TARGET_VERSION/settings.json" ] && \
  cp "$BACKUP_DIR/$TARGET_VERSION/settings.json" ~/.claude/settings.json

# Update version pointer
echo "{\"version\": \"$TARGET_VERSION\"}" > "$BACKUP_DIR/latest.json"

echo "✅ Rollback complete!"
echo "   From: $CURRENT"
echo "   To:   $TARGET_VERSION"
echo "   Backup saved: ${CURRENT}.pre_rollback"
```

### Verification After Rollback

```bash
# 1. Check version
cat ~/.stravinsky/rollback/backups/latest.json

# 2. Verify files present
ls -la ~/.claude/hooks/ | head -5
ls -la ~/.claude/commands/ | head -5
cat ~/.claude/settings.json | jq . | head -10

# 3. Test hooks (syntax check)
# If you have a hook parser:
python3 -c "from mcp_bridge.hooks import parse_hook_file; ..."

# 4. Restart Claude Code
# Close and reopen Claude Code for changes to take effect
```

---

## Emergency Procedures

**Use when**: Normal recovery procedures don't work

### Emergency Checklist

- [ ] **Step 1**: Check audit log for what happened
- [ ] **Step 2**: Verify backups exist and are readable
- [ ] **Step 3**: Try Level 1, 2, or 3 recovery
- [ ] **Step 4**: Try alternate recovery method (manual commands)
- [ ] **Step 5**: If still stuck, follow Emergency Recovery below

### Check Audit Log

```bash
# See recent operations
cat ~/.stravinsky/rollback/audit/operations.log | tail -20

# Pretty-print latest event
cat ~/.stravinsky/rollback/audit/operations.log | \
  tail -1 | python3 -m json.tool

# Query audit database
sqlite3 ~/.stravinsky/rollback/audit/audit.db \
  "SELECT event_type, version, status, error FROM audit_events ORDER BY timestamp DESC LIMIT 10;"
```

### Verify Backups Readable

```bash
# List all backups
ls -la ~/.stravinsky/rollback/backups/

# Check manifest integrity
for version in ~/.stravinsky/rollback/backups/*/; do
  version_name=$(basename "$version")
  echo "Checking $version_name..."

  if [ -f "$version/manifest.json" ]; then
    python3 -m json.tool < "$version/manifest.json" > /dev/null && \
      echo "  ✅ manifest.json valid" || \
      echo "  ❌ manifest.json corrupted"
  else
    echo "  ❌ manifest.json missing"
  fi
done

# Test tar archive extraction
tar tzf ~/.stravinsky/rollback/backups/v0.3.8/hooks.tar.gz > /dev/null && \
  echo "✅ hooks.tar.gz readable" || \
  echo "❌ hooks.tar.gz corrupted"
```

### Emergency Recovery

**If all else fails, use manual file restoration**:

```bash
# 1. Create fresh directories
rm -rf ~/.claude/hooks ~/.claude/commands 2>/dev/null
mkdir -p ~/.claude/hooks ~/.claude/commands

# 2. Find oldest intact backup
BACKUP_DIR="$HOME/.stravinsky/rollback/backups"
INTACT_VERSION=""

for version in $(ls -r $BACKUP_DIR); do
  if tar tzf "$BACKUP_DIR/$version/hooks.tar.gz" > /dev/null 2>&1; then
    INTACT_VERSION="$version"
    break
  fi
done

if [ -z "$INTACT_VERSION" ]; then
  echo "❌ No readable backups found"
  echo "⚠️  Manual restoration required"
  exit 1
fi

echo "Found readable backup: $INTACT_VERSION"

# 3. Extract from intact backup
tar xzf "$BACKUP_DIR/$INTACT_VERSION/hooks.tar.gz" -C ~/.
tar xzf "$BACKUP_DIR/$INTACT_VERSION/commands.tar.gz" -C ~/.
[ -f "$BACKUP_DIR/$INTACT_VERSION/settings.json" ] && \
  cp "$BACKUP_DIR/$INTACT_VERSION/settings.json" ~/.claude/settings.json

# 4. Verify
echo "✅ Files restored from $INTACT_VERSION"
```

---

## Troubleshooting

### Problem: "Backup not found"

```bash
# Check if backup directory exists
ls -la ~/.stravinsky/rollback/backups/

# If directory doesn't exist
mkdir -p ~/.stravinsky/rollback/backups

# If no backups exist
echo "⚠️  No backups available - cannot recover"
echo "Next steps:"
echo "1. Manually restore from version control (if available)"
echo "2. Contact support with audit log"
```

### Problem: "Permission denied" during recovery

```bash
# Check permissions on backup directory
ls -la ~/.stravinsky/rollback/

# Check permissions on hooks/commands
ls -la ~/.claude/

# Fix with appropriate permissions
chmod 755 ~/.stravinsky/rollback
chmod 755 ~/.claude
chmod 644 ~/.claude/hooks/*.md
chmod 644 ~/.claude/commands/*.md

# Retry recovery
stravinsky recovery directory ~/.claude/hooks
```

### Problem: "Corrupted tar archive"

```bash
# Verify archive integrity
tar tzf ~/.stravinsky/rollback/backups/v0.3.8/hooks.tar.gz > /dev/null

# If corrupted, try to extract what you can
tar xzf ~/.stravinsky/rollback/backups/v0.3.8/hooks.tar.gz \
  -C /tmp/recovery 2>&1 | grep -i error

# Copy recovered files
cp -r /tmp/recovery/hooks/* ~/.claude/hooks/

# Use earlier backup if this one is corrupted
stravinsky recovery directory ~/.claude/hooks v0.3.7
```

### Problem: "Files extracted but not in right place"

Backups may have different directory structures. Common layouts:

```
Option 1: Global + project separate
  hooks/
  ├── global/          # From ~/.claude/hooks/
  │   ├── my_hook.md
  │   └── ...
  └── project/         # From ./.claude/hooks/
      ├── my_hook.md
      └── ...

Option 2: Merged
  hooks/
  ├── my_hook.md       # Already merged
  └── ...
```

**Solution**: Check what's in the backup

```bash
tar tzf ~/.stravinsky/rollback/backups/v0.3.8/hooks.tar.gz | head -20

# Extract to temp to inspect structure
mkdir -p /tmp/inspect
tar xzf ~/.stravinsky/rollback/backups/v0.3.8/hooks.tar.gz -C /tmp/inspect
find /tmp/inspect -type f | head -10

# Then properly extract to ~/.claude/
rm -rf /tmp/inspect
tar xzf ~/.stravinsky/rollback/backups/v0.3.8/hooks.tar.gz -C ~/.
```

### Problem: "Rollback seemed to work but changes still broken"

```bash
# 1. Verify version was actually changed
cat ~/.stravinsky/rollback/backups/latest.json

# 2. Restart Claude Code (changes take effect on restart)
# Close and reopen Claude Code window

# 3. Check if hooks/commands cached elsewhere
# Search for cache files
find ~ -name "*cache*" -path "*claude*" 2>/dev/null

# 4. Verify files actually updated
ls -lah ~/.claude/hooks/custom_hook.md

# 5. Check system is not using old cached version
# Try running tests directly
python3 -c "import mcp_bridge; ..."
```

### Problem: "All backups show same version"

This can happen if updates failed to save version numbers.

```bash
# Check version in manifest files
for v in ~/.stravinsky/rollback/backups/*/; do
  echo "$(basename $v): $(jq '.version' $v/manifest.json)"
done

# If all show same version, backups may be duplicates
# It's safe to delete older copies
rm -rf ~/.stravinsky/rollback/backups/v0.3.8  # Keep only latest

# For recovery, use oldest available backup (safest option)
```

### Problem: "Error during manual recovery script"

```bash
# Run with debug output
bash -x recovery_script.sh 2>&1 | tee recovery.log

# Check what failed
cat recovery.log | grep -i error | head -5

# Common issues:
# 1. Wrong paths → use absolute paths with $HOME
# 2. Missing directories → mkdir -p before extracting
# 3. Permission issues → check chmod and chown
# 4. Corrupted backup → use older version
```

### Problem: "Disk full during recovery"

```bash
# Check disk space
df -h ~/

# Clean up old backups (keep last 5)
cd ~/.stravinsky/rollback/backups
ls -t | tail -n +6 | xargs rm -rf

# Try recovery again
stravinsky recovery directory ~/.claude/hooks
```

### Problem: "Rollback created but nothing changed"

```bash
# 1. Check files were actually updated
find ~/.claude -type f -newermt "10 minutes ago"

# 2. Check Claude Code is not caching
# → Close and reopen Claude Code

# 3. Verify file contents actually changed
md5sum ~/.claude/hooks/*.md

# Compare before/after
diff <(tar xzOf ~/.stravinsky/rollback/backups/v0.3.8/hooks.tar.gz | ...) \
     <(tar xzOf ~/.stravinsky/rollback/backups/v0.3.9/hooks.tar.gz | ...)

# 4. Check if rollback happened correctly
cat ~/.stravinsky/rollback/backups/latest.json
```

---

## Advanced Recovery

### Restore Specific Files from Multiple Backups

```bash
# When you need different files from different versions
# e.g., custom_hook.md from v0.3.8 but standard hooks from v0.3.9

# 1. Restore base version
stravinsky recovery directory ~/.claude/hooks v0.3.9

# 2. Selectively restore specific file
stravinsky recovery file ~/.claude/hooks/custom_hook.md v0.3.8

# 3. Verify mixed state
ls -la ~/.claude/hooks/
```

### Create Custom Recovery Point

```bash
# Before making experimental changes, create recovery point
stravinsky backup create

# Now make your changes (edit hooks, etc.)

# If something breaks, can rollback to pre-change state
stravinsky rollback list  # Find the backup timestamp
stravinsky rollback to <version>
```

### Audit Trail Analysis

```bash
# Find when a file was last modified
sqlite3 ~/.stravinsky/rollback/audit/audit.db << EOF
  SELECT timestamp, event_type, details
  FROM audit_events
  WHERE event_type LIKE '%ROLLBACK%' OR event_type LIKE '%UPDATE%'
  ORDER BY timestamp DESC;
EOF

# Export full audit trail for analysis
sqlite3 ~/.stravinsky/rollback/audit/audit.db \
  ".mode csv" \
  ".headers on" \
  "SELECT * FROM audit_events;" > ~/audit_export.csv
```

---

## When to Contact Support

If recovery doesn't work, provide:

1. **Audit log** (last 20 events):
   ```bash
   tail -20 ~/.stravinsky/rollback/audit/operations.log | \
     python3 -m json.tool > ~/support_audit.json
   ```

2. **Backup inventory**:
   ```bash
   ls -lah ~/.stravinsky/rollback/backups/ > ~/support_backups.txt
   ```

3. **Current state**:
   ```bash
   ls -la ~/.claude/hooks/ > ~/support_hooks.txt
   ls -la ~/.claude/commands/ > ~/support_commands.txt
   cat ~/.claude/settings.json > ~/support_settings.txt
   ```

4. **Error message** (verbatim)

5. **Version info**:
   ```bash
   stravinsky --version
   python3 --version
   uname -a
   ```

---

## Prevention: Avoid Recovery Situations

```bash
# 1. Keep backups of important files
cp ~/.claude/hooks/my_custom_hook.md ~/backups/

# 2. Use version control
cd ~/.claude && git init && git add . && git commit -m "Backup"

# 3. Enable additional safety in config
cat > ~/.stravinsky/rollback/config.json << EOF
{
  "safety": {
    "require_manual_confirmation_for_update": true,
    "auto_rollback_on_failure": true,
    "keep_version_copies": true
  }
}
EOF

# 4. Monitor updates
stravinsky audit log --limit 5 | watch

# 5. Test in non-critical environment first
# (If possible, test updates on separate machine before production)
```

---

## Quick Reference Commands

```bash
# See what's available
stravinsky rollback list
stravinsky backup list

# Single file recovery
stravinsky recovery file ~/.claude/hooks/custom.md

# Directory recovery
stravinsky recovery directory ~/.claude/hooks

# Full rollback
stravinsky rollback undo
stravinsky rollback to v0.3.8

# Check status
stravinsky audit log --limit 10
stravinsky backup show v0.3.8

# Emergency
stravinsky recovery emergency
```

---

**Still stuck?**

1. Read ROLLBACK_ARCHITECTURE.md for technical details
2. Check ~/.stravinsky/rollback/audit/operations.log for what happened
3. Try alternate recovery method (manual bash commands)
4. Open GitHub issue with audit log and details

**You can always recover - no data is ever permanently lost.** ✅

