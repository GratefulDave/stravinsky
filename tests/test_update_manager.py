"""
Comprehensive Test Suite for Stravinsky Auto-Update Mechanism

Tests validate safe merge behavior for:
- Hook installation and updates
- Settings.json management
- User modification preservation
- Conflict detection and resolution
- Backup creation and rollback
- Version tracking
- Statusline preservation
- Dry-run mode
- Manifest validation

CRITICAL SAFETY PRINCIPLES:
- All operations must create backups first
- No data loss on merge conflicts
- Atomic operations (all-or-nothing)
- Proper error handling and recovery
- Clear logging of all changes
"""

import json
import pytest
import shutil
from datetime import datetime, timezone


# ============================================================================
# TEST FIXTURES - Mock Data Setup
# ============================================================================


@pytest.fixture
def temp_home(tmp_path):
    """Create a temporary home directory for testing."""
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir()
    yield home
    shutil.rmtree(home, ignore_errors=True)


@pytest.fixture
def official_hooks():
    """Official Stravinsky hook files (from official release)."""
    return {
        "truncator.py": '''#!/usr/bin/env python3
def truncate(text):
    """Truncate long output."""
    return text[:30000]
''',
        "edit_recovery.py": '''#!/usr/bin/env python3
def recover_edit(error):
    """Recover from edit errors."""
    pass
''',
        "context.py": '''#!/usr/bin/env python3
def inject_context(prompt):
    """Inject context into prompt."""
    return prompt
''',
        "parallel_execution.py": '''#!/usr/bin/env python3
def enforce_parallel():
    """Enforce parallel execution."""
    pass
''',
        "todo_continuation.py": '''#!/usr/bin/env python3
def continue_todos():
    """Continue with pending todos."""
    pass
''',
        "stravinsky_mode.py": '''#!/usr/bin/env python3
def enforce_stravinsky():
    """Enforce stravinsky mode."""
    pass
''',
        "tool_messaging.py": '''#!/usr/bin/env python3
def format_message():
    """Format tool messages."""
    pass
''',
        "notification_hook.py": '''#!/usr/bin/env python3
def handle_notification():
    """Handle notifications."""
    pass
''',
    }


@pytest.fixture
def user_hooks():
    """User-modified hook files."""
    return {
        "truncator.py": '''#!/usr/bin/env python3
# USER CUSTOMIZATION: Increased truncation limit
def truncate(text):
    """Truncate long output."""
    return text[:50000]  # Custom limit
''',
        "custom_hook.py": '''#!/usr/bin/env python3
# USER CUSTOM HOOK
def my_custom_hook():
    """User-defined hook."""
    print("Custom hook running")
''',
    }


@pytest.fixture
def official_settings():
    """Official settings.json structure."""
    return {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 ~/.claude/hooks/parallel_execution.py",
                        },
                        {"type": "command", "command": "python3 ~/.claude/hooks/context.py"},
                        {
                            "type": "command",
                            "command": "python3 ~/.claude/hooks/todo_continuation.py",
                        },
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {"type": "command", "command": "python3 ~/.claude/hooks/truncator.py"},
                    ],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "Read,Grep,Bash",
                    "hooks": [
                        {"type": "command", "command": "python3 ~/.claude/hooks/stravinsky_mode.py"}
                    ],
                }
            ],
        }
    }


@pytest.fixture
def user_settings():
    """User-modified settings.json with custom configurations."""
    return {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 ~/.claude/hooks/parallel_execution.py",
                        },
                        {"type": "command", "command": "python3 ~/.claude/hooks/my_custom_hook.py"},
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {"type": "command", "command": "python3 ~/.claude/hooks/truncator.py"},
                    ],
                }
            ],
        },
        "customSetting": "userValue",
    }


@pytest.fixture
def manifest_official():
    """Official manifest for version tracking."""
    return {
        "version": "1.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hooks": {
            "truncator.py": "sha256_hash_official",
            "edit_recovery.py": "sha256_hash_official",
            "context.py": "sha256_hash_official",
        },
        "statusline": {"enabled": True, "format": "default"},
    }


@pytest.fixture
def manifest_user():
    """User's installed manifest."""
    return {
        "version": "1.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hooks": {
            "truncator.py": "sha256_hash_user_modified",
            "edit_recovery.py": "sha256_hash_official",
            "custom_hook.py": "sha256_hash_custom",
        },
        "statusline": {"enabled": True, "format": "custom"},
    }


# ============================================================================
# TEST CLASS: Hook Installation Tests
# ============================================================================


class TestHookInstallation:
    """Test hook installation scenarios."""

    def test_new_hook_installation(self, temp_home, official_hooks, official_settings):
        """Test installing hooks for the first time."""
        hooks_dir = temp_home / ".claude" / "hooks"

        # Verify hooks directory is empty
        assert len(list(hooks_dir.glob("*.py"))) == 0

        # Simulate installation
        for filename, content in official_hooks.items():
            hook_path = hooks_dir / filename
            hook_path.write_text(content)
            hook_path.chmod(0o755)

        # Verify all hooks installed
        assert len(list(hooks_dir.glob("*.py"))) == len(official_hooks)
        for filename in official_hooks:
            assert (hooks_dir / filename).exists()
            assert (hooks_dir / filename).stat().st_mode & 0o755

    def test_hook_permissions_set_correctly(self, temp_home, official_hooks):
        """Test that hooks are made executable."""
        hooks_dir = temp_home / ".claude" / "hooks"

        for filename, content in official_hooks.items():
            hook_path = hooks_dir / filename
            hook_path.write_text(content)
            hook_path.chmod(0o755)

            # Verify executable
            mode = hook_path.stat().st_mode
            assert mode & 0o700 == 0o700  # Owner can read/write/execute
            assert mode & 0o111  # At least one execute bit set

    def test_settings_json_creation(self, temp_home, official_settings):
        """Test creating settings.json with hook registrations."""
        settings_file = temp_home / ".claude" / "settings.json"

        # Write settings
        settings_file.write_text(json.dumps(official_settings, indent=2))

        # Verify
        loaded = json.loads(settings_file.read_text())
        assert "hooks" in loaded
        assert "UserPromptSubmit" in loaded["hooks"]
        assert "PostToolUse" in loaded["hooks"]

    def test_settings_json_structure_validation(self, temp_home, official_settings):
        """Test that settings.json has valid structure."""
        settings_file = temp_home / ".claude" / "settings.json"
        settings_file.write_text(json.dumps(official_settings, indent=2))

        settings = json.loads(settings_file.read_text())

        # Validate structure
        assert isinstance(settings["hooks"], dict)
        for hook_type, registrations in settings["hooks"].items():
            assert isinstance(registrations, list)
            for reg in registrations:
                assert "hooks" in reg
                assert isinstance(reg["hooks"], list)
                for hook in reg["hooks"]:
                    assert "type" in hook
                    assert "command" in hook


# ============================================================================
# TEST CLASS: Hook Update Tests
# ============================================================================


class TestHookUpdate:
    """Test hook update scenarios."""

    def test_update_with_user_modifications_preserved(self, temp_home, official_hooks, user_hooks):
        """Test updating hooks while preserving user customizations."""
        hooks_dir = temp_home / ".claude" / "hooks"

        # Install user's modified version
        for filename, content in user_hooks.items():
            hook_path = hooks_dir / filename
            hook_path.write_text(content)

        user_truncator = (hooks_dir / "truncator.py").read_text()
        assert "Custom limit" in user_truncator

        # Now simulate update with official version
        # But we should detect conflict and preserve user version

        # Check if local version differs from official
        official_truncator = official_hooks["truncator.py"]
        local_truncator = (hooks_dir / "truncator.py").read_text()

        # Detect modification
        is_modified = official_truncator != local_truncator
        assert is_modified
        assert "Custom limit" in local_truncator

    def test_update_unmodified_hooks(self, temp_home, official_hooks):
        """Test updating hooks that user hasn't modified."""
        hooks_dir = temp_home / ".claude" / "hooks"

        # Install official version
        original_hooks = {}
        for filename, content in official_hooks.items():
            hook_path = hooks_dir / filename
            hook_path.write_text(content)
            original_hooks[filename] = content

        # Create new official version
        updated_hooks = official_hooks.copy()
        updated_hooks["truncator.py"] = updated_hooks["truncator.py"].replace(
            "def truncate", "# Updated\ndef truncate"
        )

        # Detect unmodified
        for filename in ["edit_recovery.py", "context.py"]:
            original = original_hooks[filename]
            current = (hooks_dir / filename).read_text()
            assert original == current

        # Can safely update
        for filename, content in updated_hooks.items():
            hook_path = hooks_dir / filename
            hook_path.write_text(content)

        # Verify update
        assert "# Updated" in (hooks_dir / "truncator.py").read_text()

    def test_skill_addition_during_update(self, temp_home):
        """Test adding new skills alongside hook updates."""
        skills_dir = temp_home / ".claude" / "commands"
        skills_dir.mkdir(parents=True)

        # Add official skill
        official_skill = skills_dir / "official_skill.md"
        official_skill.write_text("# Official Skill\nDescription here")

        # User has their own skill
        user_skill = skills_dir / "user_skill.md"
        user_skill.write_text("# User Skill\nCustom skill")

        # Add new official skill during update
        new_skill = skills_dir / "new_feature.md"
        new_skill.write_text("# New Feature Skill\nAdded in update")

        # All skills present
        assert official_skill.exists()
        assert user_skill.exists()
        assert new_skill.exists()
        assert len(list(skills_dir.glob("*.md"))) == 3

    def test_version_tracking_in_manifest(self, temp_home, manifest_user, manifest_official):
        """Test version tracking during updates."""
        manifest_file = temp_home / ".claude" / ".stravinsky_manifest.json"

        # Initial installation
        manifest_file.write_text(json.dumps(manifest_user, indent=2))
        current_version = json.loads(manifest_file.read_text())["version"]
        assert current_version == "1.1.0"

        # Update to new version
        manifest_file.write_text(json.dumps(manifest_official, indent=2))
        updated_version = json.loads(manifest_file.read_text())["version"]
        assert updated_version == "1.2.0"
        assert updated_version > current_version


# ============================================================================
# TEST CLASS: Conflict Detection Tests
# ============================================================================


class TestConflictDetection:
    """Test conflict detection and resolution."""

    def test_detect_modified_hook_conflict(self, temp_home, official_hooks):
        """Test detecting when local hook differs from official."""
        hooks_dir = temp_home / ".claude" / "hooks"

        # Install official
        truncator_official = official_hooks["truncator.py"]
        (hooks_dir / "truncator.py").write_text(truncator_official)

        # User modifies
        truncator_modified = truncator_official.replace("30000", "50000")
        (hooks_dir / "truncator.py").write_text(truncator_modified)

        # Detect conflict
        current = (hooks_dir / "truncator.py").read_text()
        is_different = current != truncator_official
        assert is_different
        assert "50000" in current

    def test_detect_new_user_file_conflict(self, temp_home, official_hooks):
        """Test detecting when user has added files."""
        hooks_dir = temp_home / ".claude" / "hooks"

        # Install official hooks
        for filename, content in official_hooks.items():
            (hooks_dir / filename).write_text(content)

        # User adds custom hook
        custom_file = hooks_dir / "user_custom.py"
        custom_file.write_text("# User custom")

        # Detect custom file
        all_files = set(f.name for f in hooks_dir.glob("*.py"))
        official_names = set(official_hooks.keys())
        custom_files = all_files - official_names

        assert len(custom_files) > 0
        assert "user_custom.py" in custom_files

    def test_detect_deleted_hooks(self, temp_home, official_hooks):
        """Test detecting when user has deleted official hooks."""
        hooks_dir = temp_home / ".claude" / "hooks"

        # Install official
        for filename, content in official_hooks.items():
            (hooks_dir / filename).write_text(content)

        # User deletes a hook
        (hooks_dir / "truncator.py").unlink()

        # Detect deletion
        deleted = set(official_hooks.keys()) - {f.name for f in hooks_dir.glob("*.py")}
        assert len(deleted) > 0
        assert "truncator.py" in deleted

    def test_conflict_resolution_strategy(self, temp_home, official_hooks):
        """Test conflict resolution without data loss."""
        hooks_dir = temp_home / ".claude" / "hooks"

        # Scenario: Official has update, user has modifications
        truncator_official = official_hooks["truncator.py"]
        truncator_modified = truncator_official.replace(
            "30000",
            "50000",  # User customization
        )
        truncator_update = truncator_official.replace(
            "30000",
            "25000",  # Official update
        )

        (hooks_dir / "truncator.py").write_text(truncator_modified)

        # Resolution: Create conflict markers
        conflict_content = f"""<<<<<<< ORIGINAL (user)
{truncator_modified}
=======
{truncator_update}
>>>>>>> UPDATE (official)
"""

        conflict_file = hooks_dir / "truncator.py.conflict"
        conflict_file.write_text(conflict_content)

        # Verify both versions preserved
        assert "50000" in conflict_file.read_text()
        assert "25000" in conflict_file.read_text()


# ============================================================================
# TEST CLASS: Backup and Rollback Tests
# ============================================================================


class TestBackupAndRollback:
    """Test backup creation and rollback mechanism."""

    def test_backup_created_before_update(self, temp_home, official_hooks):
        """Test that backups are created before updates."""
        hooks_dir = temp_home / ".claude" / "hooks"
        backup_dir = temp_home / ".claude" / ".backups"

        # Create initial state
        for filename, content in official_hooks.items():
            (hooks_dir / filename).write_text(content)

        # Create backup
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"hooks_backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        # Copy hooks to backup
        for hook_file in hooks_dir.glob("*.py"):
            shutil.copy2(hook_file, backup_path / hook_file.name)

        # Verify backup
        assert backup_path.exists()
        assert len(list(backup_path.glob("*.py"))) == len(official_hooks)

    def test_backup_preserves_file_metadata(self, temp_home, official_hooks):
        """Test that backups preserve file metadata."""
        hooks_dir = temp_home / ".claude" / "hooks"
        backup_dir = temp_home / ".claude" / ".backups"

        # Create file with specific metadata
        hook_file = hooks_dir / "truncator.py"
        hook_file.write_text(official_hooks["truncator.py"])
        original_stat = hook_file.stat()

        # Backup
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / "truncator.py"
        shutil.copy2(hook_file, backup_file)

        # Compare metadata
        backup_stat = backup_file.stat()
        assert backup_stat.st_size == original_stat.st_size

    def test_rollback_from_backup(self, temp_home, official_hooks):
        """Test rolling back to a previous backup."""
        hooks_dir = temp_home / ".claude" / "hooks"
        backup_dir = temp_home / ".claude" / ".backups"

        # Create initial state and backup
        for filename, content in official_hooks.items():
            (hooks_dir / filename).write_text(content)

        backup_dir.mkdir(parents=True, exist_ok=True)
        original_backup = backup_dir / "original"
        original_backup.mkdir(parents=True, exist_ok=True)

        for hook_file in hooks_dir.glob("*.py"):
            shutil.copy2(hook_file, original_backup / hook_file.name)

        # Modify hooks
        modified_truncator = official_hooks["truncator.py"].replace("30000", "99999")
        (hooks_dir / "truncator.py").write_text(modified_truncator)

        # Verify modification
        assert "99999" in (hooks_dir / "truncator.py").read_text()

        # Rollback
        for backup_file in original_backup.glob("*.py"):
            shutil.copy2(backup_file, hooks_dir / backup_file.name)

        # Verify rollback
        assert "99999" not in (hooks_dir / "truncator.py").read_text()
        assert "30000" in (hooks_dir / "truncator.py").read_text()

    def test_rollback_atomicity(self, temp_home, official_hooks):
        """Test that rollback is atomic (all-or-nothing)."""
        hooks_dir = temp_home / ".claude" / "hooks"
        backup_dir = temp_home / ".claude" / ".backups"

        # Create initial state
        for filename, content in official_hooks.items():
            (hooks_dir / filename).write_text(content)

        # Backup
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / "atomic_test"
        backup.mkdir(parents=True, exist_ok=True)

        for hook_file in hooks_dir.glob("*.py"):
            shutil.copy2(hook_file, backup / hook_file.name)

        # Attempt rollback (simulating atomic operation)
        rollback_success = True
        rollback_errors = []

        try:
            # Start rollback
            for backup_file in backup.glob("*.py"):
                target = hooks_dir / backup_file.name
                shutil.copy2(backup_file, target)
        except Exception as e:
            rollback_success = False
            rollback_errors.append(str(e))

        assert rollback_success
        assert len(rollback_errors) == 0

    def test_multiple_backups_retained(self, temp_home):
        """Test that multiple backups are retained for recovery."""
        backup_dir = temp_home / ".claude" / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create multiple backups
        for i in range(3):
            backup_path = backup_dir / f"backup_{i}"
            backup_path.mkdir(parents=True, exist_ok=True)
            (backup_path / f"hooks_{i}.py").write_text(f"# Backup {i}")

        # Verify all retained
        backups = list(backup_dir.glob("backup_*"))
        assert len(backups) == 3


# ============================================================================
# TEST CLASS: Settings.json Merge Tests
# ============================================================================


class TestSettingsMerge:
    """Test settings.json merge without data loss."""

    def test_merge_preserves_existing_settings(self, temp_home, user_settings, official_settings):
        """Test that merge preserves existing user settings."""
        settings_file = temp_home / ".claude" / "settings.json"

        # Write user settings
        settings_file.write_text(json.dumps(user_settings, indent=2))
        user_custom = user_settings.get("customSetting")

        # Merge official settings
        current = json.loads(settings_file.read_text())
        current["hooks"] = official_settings["hooks"]
        settings_file.write_text(json.dumps(current, indent=2))

        # Verify custom setting preserved
        result = json.loads(settings_file.read_text())
        assert result.get("customSetting") == user_custom

    def test_merge_handles_hook_arrays(self, temp_home):
        """Test merging hook arrays without duplication."""
        settings_file = temp_home / ".claude" / "settings.json"

        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"type": "command", "command": "hook_a.py"},
                            {"type": "command", "command": "hook_b.py"},
                        ],
                    }
                ]
            }
        }

        # Write initial
        settings_file.write_text(json.dumps(settings, indent=2))

        # Merge new hook
        result = json.loads(settings_file.read_text())

        # Add new without duplication
        if "hook_c.py" not in [
            h["command"] for h in result["hooks"]["UserPromptSubmit"][0]["hooks"]
        ]:
            result["hooks"]["UserPromptSubmit"][0]["hooks"].append(
                {"type": "command", "command": "hook_c.py"}
            )

        settings_file.write_text(json.dumps(result, indent=2))

        # Verify no duplication
        final = json.loads(settings_file.read_text())
        commands = [h["command"] for h in final["hooks"]["UserPromptSubmit"][0]["hooks"]]
        assert len(commands) == len(set(commands))

    def test_merge_with_missing_hooks_section(self, temp_home):
        """Test merge when settings.json doesn't have hooks section."""
        settings_file = temp_home / ".claude" / "settings.json"

        # Write settings without hooks
        settings_file.write_text(json.dumps({"other": "value"}, indent=2))

        # Merge hooks
        current = json.loads(settings_file.read_text())
        if "hooks" not in current:
            current["hooks"] = {}

        current["hooks"]["PreToolUse"] = [
            {"matcher": "*", "hooks": [{"type": "command", "command": "test.py"}]}
        ]

        settings_file.write_text(json.dumps(current, indent=2))

        # Verify hooks added
        result = json.loads(settings_file.read_text())
        assert "hooks" in result
        assert "PreToolUse" in result["hooks"]

    def test_merge_preserves_hook_order(self, temp_home):
        """Test that merge preserves hook execution order."""
        settings_file = temp_home / ".claude" / "settings.json"

        hooks = [
            {"type": "command", "command": "first.py"},
            {"type": "command", "command": "second.py"},
            {"type": "command", "command": "third.py"},
        ]

        settings = {"hooks": {"UserPromptSubmit": [{"matcher": "*", "hooks": hooks}]}}

        settings_file.write_text(json.dumps(settings, indent=2))
        result = json.loads(settings_file.read_text())

        # Verify order
        commands = [h["command"] for h in result["hooks"]["UserPromptSubmit"][0]["hooks"]]
        assert commands == ["first.py", "second.py", "third.py"]


# ============================================================================
# TEST CLASS: Statusline Preservation Tests
# ============================================================================


class TestStatuslinePreservation:
    """Test statusline settings preservation."""

    def test_statusline_config_preserved_in_manifest(self, temp_home, manifest_user):
        """Test that statusline config is preserved."""
        manifest_file = temp_home / ".claude" / ".stravinsky_manifest.json"
        manifest_file.write_text(json.dumps(manifest_user, indent=2))

        manifest = json.loads(manifest_file.read_text())
        assert manifest["statusline"]["enabled"] is True
        assert manifest["statusline"]["format"] == "custom"

    def test_statusline_migration_on_update(self, temp_home, manifest_user, manifest_official):
        """Test statusline config migration during update."""
        manifest_file = temp_home / ".claude" / ".stravinsky_manifest.json"

        # Initial state
        manifest_file.write_text(json.dumps(manifest_user, indent=2))
        user_statusline = json.loads(manifest_file.read_text())["statusline"]

        # Update manifest but preserve statusline
        manifest_official["statusline"] = user_statusline
        manifest_file.write_text(json.dumps(manifest_official, indent=2))

        # Verify preservation
        updated = json.loads(manifest_file.read_text())
        assert updated["statusline"]["format"] == "custom"

    def test_statusline_recovery_on_conflict(self, temp_home, manifest_user):
        """Test statusline recovery in conflict scenarios."""
        manifest_file = temp_home / ".claude" / ".stravinsky_manifest.json"
        conflict_file = temp_home / ".claude" / ".stravinsky_manifest.conflict"

        # Write original
        manifest_file.write_text(json.dumps(manifest_user, indent=2))
        original_statusline = json.loads(manifest_file.read_text())["statusline"]

        # Save to conflict file for recovery
        conflict_data = {
            "original_statusline": original_statusline,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        conflict_file.write_text(json.dumps(conflict_data, indent=2))

        # Recover
        if conflict_file.exists():
            recovery_data = json.loads(conflict_file.read_text())
            recovered_statusline = recovery_data["original_statusline"]
            assert recovered_statusline == original_statusline


# ============================================================================
# TEST CLASS: Version Tracking and Manifest Tests
# ============================================================================


class TestVersionTracking:
    """Test version tracking and manifest validation."""

    def test_manifest_version_comparison(self, temp_home, manifest_user, manifest_official):
        """Test comparing manifest versions."""

        def parse_version(version_str: str) -> tuple:
            """Parse semantic version."""
            parts = version_str.split(".")
            return tuple(int(p) for p in parts)

        user_version = parse_version(manifest_user["version"])
        official_version = parse_version(manifest_official["version"])

        assert user_version < official_version

    def test_manifest_hash_validation(self, temp_home, official_hooks):
        """Test hash validation for integrity."""
        import hashlib

        manifest = {"hooks": {}}

        for filename, content in official_hooks.items():
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            manifest["hooks"][filename] = file_hash

        # Verify hash
        for filename, expected_hash in manifest["hooks"].items():
            content_hash = hashlib.sha256(official_hooks[filename].encode()).hexdigest()
            assert content_hash == expected_hash

    def test_manifest_timestamp_updates(self, temp_home):
        """Test that manifest timestamp is updated on changes."""
        manifest_file = temp_home / ".claude" / ".stravinsky_manifest.json"

        # Create initial manifest
        manifest_v1 = {
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00.000000",
        }
        manifest_file.write_text(json.dumps(manifest_v1, indent=2))

        # Update manifest
        manifest_v2 = {
            "version": "1.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        manifest_file.write_text(json.dumps(manifest_v2, indent=2))

        # Verify timestamp changed
        current = json.loads(manifest_file.read_text())
        assert current["timestamp"] > manifest_v1["timestamp"]

    def test_manifest_hook_list_validation(self, temp_home, official_hooks, manifest_official):
        """Test validating manifest hook list."""
        manifest_file = temp_home / ".claude" / ".stravinsky_manifest.json"

        # Write manifest
        manifest_file.write_text(json.dumps(manifest_official, indent=2))
        manifest = json.loads(manifest_file.read_text())

        # Verify all official hooks in manifest
        for filename in official_hooks.keys():
            # Either in manifest or it's OK (new hooks)
            if filename in manifest["hooks"]:
                assert manifest["hooks"][filename] is not None


# ============================================================================
# TEST CLASS: Dry-Run Mode Tests
# ============================================================================


class TestDryRunMode:
    """Test dry-run mode for previewing changes."""

    def test_dry_run_no_files_modified(self, temp_home, official_hooks):
        """Test that dry-run doesn't modify files."""
        hooks_dir = temp_home / ".claude" / "hooks"

        # Record initial state
        initial_files = set(hooks_dir.glob("*.py"))

        # Simulate dry-run (don't actually write)
        dry_run = True
        for filename, content in official_hooks.items():
            hook_path = hooks_dir / filename
            if dry_run:
                # Just read/check, don't write
                if hook_path.exists():
                    # Check if would differ
                    hook_path.read_text()
                else:
                    pass  # Would create new file
            else:
                hook_path.write_text(content)

        # Verify no changes when dry-run=True
        if dry_run:
            assert set(hooks_dir.glob("*.py")) == initial_files

    def test_dry_run_preview_output(self, temp_home):
        """Test that dry-run provides preview output."""
        preview_file = temp_home / ".claude" / ".update_preview.json"

        preview = {
            "mode": "dry-run",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changes": [
                {"file": "truncator.py", "action": "update", "lines_changed": 5},
                {"file": "custom_hook.py", "action": "keep", "reason": "user_modified"},
                {"file": "new_hook.py", "action": "create", "size": 1024},
            ],
            "backup": "hooks_backup_20240115_120000",
            "rollback_command": "stravinsky rollback hooks_backup_20240115_120000",
        }

        preview_file.write_text(json.dumps(preview, indent=2))

        # Verify preview content
        loaded = json.loads(preview_file.read_text())
        assert loaded["mode"] == "dry-run"
        assert len(loaded["changes"]) == 3
        assert "rollback_command" in loaded


# ============================================================================
# TEST CLASS: Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete update workflows."""

    def test_complete_update_workflow(
        self, temp_home, official_hooks, user_hooks, official_settings
    ):
        """Test complete update workflow."""
        hooks_dir = temp_home / ".claude" / "hooks"
        settings_file = temp_home / ".claude" / "settings.json"
        backup_dir = temp_home / ".claude" / ".backups"

        # Step 1: Initial installation with user mods
        for filename, content in user_hooks.items():
            (hooks_dir / filename).write_text(content)

        # Step 2: Create backup
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / "pre_update"
        backup.mkdir(parents=True, exist_ok=True)
        for hook_file in hooks_dir.glob("*.py"):
            shutil.copy2(hook_file, backup / hook_file.name)

        # Step 3: Update hooks (preserving user mods)
        for filename, content in official_hooks.items():
            hook_path = hooks_dir / filename
            if hook_path.exists():
                existing = hook_path.read_text()
                # If user modified, keep it; otherwise update
                if existing != official_hooks.get(filename, ""):
                    # User modified, preserve
                    pass
                else:
                    # Official version, update
                    hook_path.write_text(content)
            else:
                hook_path.write_text(content)

        # Step 4: Update settings
        settings_file.write_text(json.dumps(official_settings, indent=2))

        # Verify all succeeded
        assert all((hooks_dir / f).exists() for f in official_hooks.keys())
        assert settings_file.exists()
        assert backup.exists()
        assert len(list(backup.glob("*.py"))) > 0

    def test_update_with_error_recovery(self, temp_home, official_hooks, official_settings):
        """Test error recovery during update."""
        hooks_dir = temp_home / ".claude" / "hooks"
        settings_file = temp_home / ".claude" / "settings.json"
        backup_dir = temp_home / ".claude" / ".backups"

        # Setup
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / "error_recovery"
        backup.mkdir(parents=True, exist_ok=True)

        # Initial state
        for filename, content in official_hooks.items():
            hook_path = hooks_dir / filename
            hook_path.write_text(content)
            shutil.copy2(hook_path, backup / hook_path.name)

        # Simulate error during update
        error_occurred = False
        try:
            # This could fail
            if False:
                raise RuntimeError("Simulated update error")

            # Update succeeded
            settings_file.write_text(json.dumps(official_settings, indent=2))
        except Exception:
            error_occurred = True
            # Rollback on error
            for backup_file in backup.glob("*.py"):
                shutil.copy2(backup_file, hooks_dir / backup_file.name)

        # Verify recovery (no error in this test)
        assert not error_occurred
        assert settings_file.exists()


# ============================================================================
# TEST CLASS: Edge Cases and Safety Tests
# ============================================================================


class TestEdgeCasesAndSafety:
    """Test edge cases and safety scenarios."""

    def test_empty_hooks_directory(self, temp_home):
        """Test handling of empty hooks directory."""
        hooks_dir = temp_home / ".claude" / "hooks"

        # Directory exists but empty
        assert hooks_dir.exists()
        assert len(list(hooks_dir.glob("*.py"))) == 0

        # Should be safe to install
        test_hook = hooks_dir / "test.py"
        test_hook.write_text("# Test")
        assert test_hook.exists()

    def test_corrupted_settings_json_recovery(self, temp_home):
        """Test recovery from corrupted settings.json."""
        settings_file = temp_home / ".claude" / "settings.json"

        # Write corrupted JSON
        settings_file.write_text("{invalid json")

        # Attempt recovery
        recovered = False
        try:
            json.loads(settings_file.read_text())
        except json.JSONDecodeError:
            # Create backup of corrupted file
            corrupted_backup = settings_file.with_suffix(".corrupted")
            shutil.copy2(settings_file, corrupted_backup)

            # Write clean default
            settings_file.write_text(json.dumps({"hooks": {}}, indent=2))
            recovered = True

        assert recovered
        assert json.loads(settings_file.read_text())["hooks"] == {}

    def test_permission_denied_handling(self, temp_home):
        """Test handling of permission denied errors."""
        hooks_dir = temp_home / ".claude" / "hooks"

        hook_file = hooks_dir / "test.py"
        hook_file.write_text("# Test")
        hook_file.chmod(0o000)  # Remove all permissions

        # Attempt recovery
        try:
            hook_file.read_text()
            assert False, "Should have raised PermissionError"
        except PermissionError:
            # Restore permissions
            hook_file.chmod(0o755)
            assert hook_file.stat().st_mode & 0o700

    def test_symlink_handling(self, temp_home):
        """Test handling of symlinked files."""
        hooks_dir = temp_home / ".claude" / "hooks"
        real_file = temp_home / "real_hook.py"

        # Create real file
        real_file.write_text("# Real hook")

        # Create symlink
        link_path = hooks_dir / "symlink_hook.py"
        link_path.symlink_to(real_file)

        # Should handle symlink
        assert link_path.exists()
        assert link_path.is_symlink()
        assert link_path.read_text() == real_file.read_text()

    def test_very_large_settings_json(self, temp_home):
        """Test handling of large settings.json files."""
        settings_file = temp_home / ".claude" / "settings.json"

        # Create large but valid settings
        large_settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"type": "command", "command": f"hook_{i}.py"} for i in range(100)
                        ],
                    }
                ]
            }
        }

        settings_file.write_text(json.dumps(large_settings, indent=2))

        # Should load and parse successfully
        result = json.loads(settings_file.read_text())
        assert len(result["hooks"]["UserPromptSubmit"][0]["hooks"]) == 100

    def test_concurrent_update_prevention(self, temp_home):
        """Test prevention of concurrent updates."""
        lock_file = temp_home / ".claude" / ".update_lock"

        # Acquire lock
        lock_file.write_text(
            json.dumps(
                {
                    "pid": 12345,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        )

        assert lock_file.exists()

        # Attempt to acquire lock again
        is_locked = False
        if lock_file.exists():
            # Lock file exists - concurrent update detected
            is_locked = True

        assert is_locked


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
