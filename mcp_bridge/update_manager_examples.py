#!/usr/bin/env python3
"""
Examples for using the Stravinsky Update Manager.

Demonstrates typical workflows for updating hooks, handling conflicts, and rollback.
"""

from pathlib import Path
from update_manager import UpdateManager


# Example 1: Simple Update During Server Startup
# ================================================

def example_startup_update():
    """Called during Stravinsky server startup to auto-update hooks."""
    from mcp_bridge.cli.install_hooks import HOOKS
    from mcp_bridge import __version__

    manager = UpdateManager(dry_run=False, verbose=False)

    # Update hooks to latest version
    success, conflicts = manager.update_hooks(HOOKS, __version__)

    if success:
        print(f"✓ Hooks updated to {__version__}")
    else:
        print("✗ Update failed")
        return False

    # Report any conflicts
    if conflicts:
        print(f"\n⚠️ {len(conflicts)} conflicts detected:")
        for conflict in conflicts:
            print(f"\n  File: {conflict.file_path}")
            print(f"  Type: {conflict.conflict_type}")
            print("  Action: Edit file to resolve, removing conflict markers")
        return False

    return True


# Example 2: Test Update with Dry-Run
# ====================================

def example_dry_run_test():
    """Test what would happen without making changes."""
    from mcp_bridge.cli.install_hooks import HOOKS
    from mcp_bridge import __version__

    manager = UpdateManager(dry_run=True, verbose=True)

    print("🧪 Testing update (dry-run mode)...")
    success, conflicts = manager.update_hooks(HOOKS, __version__)

    if conflicts:
        print(f"\n⚠️ Would have {len(conflicts)} conflicts")
    else:
        print("✓ Update would succeed without conflicts")

    print("\n(No actual changes were made)")


# Example 3: Verify Installation Health
# ======================================

def example_verify_installation():
    """Check if hooks and settings are installed correctly."""
    manager = UpdateManager()

    is_valid, issues = manager.verify_integrity()

    if is_valid:
        print("✓ Installation is valid and healthy")
    else:
        print("✗ Issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    return True


# Example 4: List and Manage Backups
# ==================================

def example_backup_management():
    """List and analyze backups."""
    manager = UpdateManager()

    backups = manager.list_backups()

    if not backups:
        print("No backups found")
        return

    print(f"📦 Found {len(backups)} backups:\n")

    for i, backup in enumerate(backups, 1):
        print(f"{i}. {backup['name']}")
        print(f"   Size: {backup['size_mb']:.2f} MB")
        print(f"   Created: {backup['created']}")
        print()


# Example 5: Rollback to Previous State
# =====================================

def example_rollback():
    """Rollback to a previous backup."""
    manager = UpdateManager()

    # Get available backups
    backups = manager.list_backups()

    if not backups:
        print("No backups available for rollback")
        return False

    # Use most recent backup
    latest = backups[0]
    timestamp = latest['name'].split('_')[-2] + '_' + latest['name'].split('_')[-1]

    print(f"Rolling back to {timestamp}...")
    success = manager.rollback(timestamp)

    if success:
        print("✓ Rollback successful")
        print(f"  Restored: {latest['name']}")
    else:
        print("✗ Rollback failed")

    return success


# Example 6: Handle Update Conflicts
# ==================================

def example_handle_conflicts():
    """Handle merge conflicts during update."""
    from mcp_bridge.cli.install_hooks import HOOKS
    from mcp_bridge import __version__

    manager = UpdateManager(dry_run=False, verbose=True)

    print("Starting update with conflict handling...\n")

    success, conflicts = manager.update_hooks(HOOKS, __version__)

    if conflicts:
        print(f"\n❌ Found {len(conflicts)} conflicts:\n")

        for conflict in conflicts:
            print(f"📄 {conflict.file_path}")
            print(f"   Conflict Type: {conflict.conflict_type}")
            print(f"   User Version: {conflict.user_version}")
            print(f"   New Version: {conflict.new_version}")
            print()

        print("✏️  Manual Resolution Steps:")
        print("1. Edit the conflicted files in ~/.claude/hooks/")
        print("2. Look for lines with: <<<<<<< USER VERSION / =======  / >>>>>>> NEW VERSION")
        print("3. Keep the content you want (remove the other)")
        print("4. Remove all conflict markers")
        print("5. Test with: python mcp_bridge/update_manager.py --verify")
        return False

    print("✓ Update completed with no conflicts")
    return True


# Example 7: Update Settings.json with Hook Merge
# ================================================

def example_update_settings():
    """Update settings.json while preserving user configuration."""
    manager = UpdateManager()

    # New settings from Stravinsky package
    new_settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Read,Search,Grep,Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 ~/.claude/hooks/stravinsky_mode.py"
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 ~/.claude/hooks/truncator.py"
                        }
                    ]
                }
            ]
        }
    }

    print("Updating settings.json...")
    success, conflicts = manager.update_settings_json(new_settings)

    if success:
        print("✓ settings.json updated")
        print("  ✓ Statusline preserved")
        print("  ✓ User hooks merged")
    else:
        print("✗ Update failed")

    if conflicts:
        print(f"\n⚠️ {len(conflicts)} conflicts in settings")


# Example 8: Integration Example for Server Startup
# =================================================

def example_server_startup_integration():
    """
    Example of how to integrate update manager into server startup.

    This would go in mcp_bridge/server.py or similar.
    """
    code = '''
import logging
from pathlib import Path
from mcp_bridge import __version__
from mcp_bridge.update_manager import UpdateManager
from mcp_bridge.cli.install_hooks import HOOKS

logger = logging.getLogger(__name__)

def startup_update_check():
    """Check and apply hook updates during server startup."""
    logger.info("Checking for hook updates...")

    try:
        manager = UpdateManager(verbose=False)

        # Verify current installation
        is_valid, issues = manager.verify_integrity()
        if not is_valid:
            logger.warning(f"Installation issues detected: {issues}")

        # Update hooks
        success, conflicts = manager.update_hooks(HOOKS, __version__)

        if success:
            logger.info(f"✓ Hooks updated to {__version__}")
        else:
            logger.error("Hook update failed")
            return False

        if conflicts:
            logger.warning(f"Update conflicts detected: {len(conflicts)} files")
            for conflict in conflicts:
                logger.warning(f"  - {conflict.file_path}: {conflict.conflict_type}")
            # Continue anyway - user can resolve manually

        return True

    except Exception as e:
        logger.error(f"Update check failed: {e}")
        # Don't fail server startup for update issues
        return True

# Call during server initialization
if __name__ == "__main__":
    startup_update_check()
    # ... rest of server initialization ...
'''
    print("Example integration code for server.py:")
    print(code)


# Run Examples
# ============

if __name__ == "__main__":
    print("Stravinsky Update Manager Examples\n")
    print("=" * 50)

    # Uncomment the example to run:

    # print("\n1. Server Startup Update\n")
    # example_startup_update()

    # print("\n2. Dry-Run Test\n")
    # example_dry_run_test()

    print("\n3. Verify Installation\n")
    example_verify_installation()

    print("\n4. Backup Management\n")
    example_backup_management()

    # print("\n5. Rollback\n")
    # example_rollback()

    # print("\n6. Handle Conflicts\n")
    # example_handle_conflicts()

    # print("\n7. Update Settings\n")
    # example_update_settings()

    print("\n8. Server Integration\n")
    example_server_startup_integration()
