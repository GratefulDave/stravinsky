#!/usr/bin/env python3
"""
Hook & Skill Merge Strategy Implementation

Validates and manages hook/skill merges during version updates.
Usage:
    python merge_strategy.py --analyze              # Detect current customizations
    python merge_strategy.py --validate             # Validate before merge
    python merge_strategy.py --migrate <old> <new>  # Migrate hook format
"""

import json
import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


class MergeStrategy:
    """Manages hook and skill merges."""

    # Hook categorization (from analysis)
    TIER_1_SYSTEM_CORE = [
        "stravinsky_mode.py",
        "parallel_execution.py",
        "todo_continuation.py",
        "stop_hook.py",
        "context.py",
        "notification_hook.py",
        "tool_messaging.py",
        "truncator.py",
        "pre_compact.py",
        "subagent_stop.py",
    ]

    TIER_2_USER_FACING = [
        "context_monitor.py",
        "edit_recovery.py",
    ]

    # User-customizable fields by hook
    CUSTOMIZABLE_FIELDS = {
        "context_monitor.py": {
            "MAX_CONTEXT_TOKENS": (100000, 500000, 200000),  # (min, max, default)
            "PREEMPTIVE_THRESHOLD": (0.50, 0.80, 0.70),
            "CRITICAL_THRESHOLD": (0.75, 0.95, 0.85),
            "CHARS_PER_TOKEN": (3, 5, 4),
        },
        "edit_recovery.py": {
            "error_patterns": None,  # List - check if modified
        },
    }

    def __init__(self, project_root: Path = None):
        """Initialize merge strategy checker."""
        self.project_root = project_root or Path.cwd()
        self.hooks_dir = self.project_root / ".claude" / "hooks"
        self.commands_dir = self.project_root / ".claude" / "commands"
        self.settings_file = self.project_root / ".claude" / "settings.json"

    def calculate_file_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of file."""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def extract_constant_values(self, filepath: Path, constants: List[str]) -> Dict[str, any]:
        """Extract constant values from Python file."""
        values = {}
        with open(filepath, "r") as f:
            content = f.read()

        for const in constants:
            # Match: CONST_NAME = value
            patterns = [
                rf'^{const}\s*=\s*(\d+)',  # Integer
                rf'^{const}\s*=\s*([\d.]+)',  # Float
                rf'^{const}\s*=\s*"([^"]*)"',  # String
                rf'^{const}\s*=\s*\'([^\']*)\'',  # String
                rf'^{const}\s*=\s*(\[.*?\])',  # List (simplified)
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.MULTILINE)
                if match:
                    value_str = match.group(1)
                    # Try to convert to appropriate type
                    try:
                        if "." in value_str:
                            values[const] = float(value_str)
                        elif value_str.isdigit():
                            values[const] = int(value_str)
                        else:
                            values[const] = value_str
                    except:
                        values[const] = value_str
                    break

        return values

    def detect_customizations(self) -> Dict[str, Dict[str, any]]:
        """Detect user customizations in TIER 2 hooks."""
        customizations = {}

        for hook_name, fields in self.CUSTOMIZABLE_FIELDS.items():
            hook_path = self.hooks_dir / hook_name
            if not hook_path.exists():
                continue

            current_values = self.extract_constant_values(
                hook_path, list(fields.keys())
            )

            customized = {}
            for field_name, field_info in fields.items():
                if field_info is None:  # Special handling for lists
                    # For now, skip detailed list analysis
                    continue

                min_val, max_val, default_val = field_info
                current_val = current_values.get(field_name, default_val)

                if current_val != default_val:
                    customized[field_name] = {
                        "current": current_val,
                        "default": default_val,
                        "range": (min_val, max_val),
                    }

            if customized:
                customizations[hook_name] = customized

        return customizations

    def validate_settings_json(self) -> Tuple[bool, List[str]]:
        """Validate settings.json structure."""
        issues = []

        if not self.settings_file.exists():
            return False, ["settings.json not found"]

        try:
            with open(self.settings_file) as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]

        # Check for required hook entry points
        required_hooks = {
            "Notification": "notification_hook.py",
            "SubagentStop": "subagent_stop.py",
            "PreCompact": "pre_compact.py",
            "PreToolUse": "stravinsky_mode.py",
            "UserPromptSubmit": "context_monitor.py",  # One of many
        }

        hooks_section = settings.get("hooks", {})

        for lifecycle, expected_hook in required_hooks.items():
            if lifecycle not in hooks_section:
                issues.append(f"Missing lifecycle: {lifecycle}")
            else:
                # Check if any hook entry contains the expected hook
                found = False
                for entry in hooks_section[lifecycle]:
                    for hook in entry.get("hooks", []):
                        if expected_hook in hook.get("command", ""):
                            found = True
                            break
                if not found:
                    issues.append(
                        f"Missing hook in {lifecycle}: {expected_hook}"
                    )

        return len(issues) == 0, issues

    def analyze_merge_type(
        self, new_hooks_dir: Path
    ) -> Tuple[str, List[str], Dict[str, any]]:
        """
        Analyze type of merge needed.

        Returns: (merge_type, affected_files, details)
        """
        affected = []
        details = {}

        # Check TIER 1 files
        tier1_changed = []
        for hook_name in self.TIER_1_SYSTEM_CORE:
            old_path = self.hooks_dir / hook_name
            new_path = new_hooks_dir / hook_name

            if not old_path.exists() or not new_path.exists():
                continue

            old_hash = self.calculate_file_hash(old_path)
            new_hash = self.calculate_file_hash(new_path)

            if old_hash != new_hash:
                tier1_changed.append(hook_name)
                affected.append(f"TIER 1: {hook_name}")

        # Check TIER 2 files
        tier2_customizations = self.detect_customizations()
        tier2_changed = []
        for hook_name in self.TIER_2_USER_FACING:
            old_path = self.hooks_dir / hook_name
            new_path = new_hooks_dir / hook_name

            if not old_path.exists() or not new_path.exists():
                continue

            old_hash = self.calculate_file_hash(old_path)
            new_hash = self.calculate_file_hash(new_path)

            if old_hash != new_hash:
                tier2_changed.append(hook_name)
                has_customizations = hook_name in tier2_customizations
                affected.append(
                    f"TIER 2: {hook_name} (customizations: {has_customizations})"
                )

        # Determine merge type
        if not tier1_changed and not tier2_changed:
            merge_type = "NO_CHANGE"
        elif tier1_changed and not tier2_changed:
            merge_type = "SYSTEM_ONLY"
        elif tier2_changed and not tier1_changed:
            if tier2_customizations:
                merge_type = "MANUAL_MERGE"
            else:
                merge_type = "AUTO_MERGE"
        else:
            if tier2_customizations:
                merge_type = "MANUAL_MERGE"
            else:
                merge_type = "FULL_MERGE"

        details = {
            "tier1_changed": tier1_changed,
            "tier2_changed": tier2_changed,
            "tier2_customizations": tier2_customizations,
        }

        return merge_type, affected, details

    def generate_merge_report(
        self, new_hooks_dir: Path
    ) -> str:
        """Generate detailed merge analysis report."""
        report_lines = [
            "=== MERGE ANALYSIS REPORT ===",
            "",
            f"Project: {self.project_root}",
            f"Hooks Directory: {self.hooks_dir}",
            "",
        ]

        # Validate current state
        valid, validation_issues = self.validate_settings_json()
        report_lines.append("VALIDATION:")
        if valid:
            report_lines.append("  ✅ settings.json is valid")
        else:
            report_lines.append("  ❌ settings.json issues:")
            for issue in validation_issues:
                report_lines.append(f"     - {issue}")
        report_lines.append("")

        # Detect customizations
        customizations = self.detect_customizations()
        report_lines.append("CUSTOMIZATIONS DETECTED:")
        if customizations:
            for hook_name, customized_fields in customizations.items():
                report_lines.append(f"  ⚙️  {hook_name}:")
                for field_name, field_info in customized_fields.items():
                    current = field_info["current"]
                    default = field_info["default"]
                    min_val, max_val = field_info["range"]
                    report_lines.append(
                        f"      {field_name}: {current} (default: {default}, range: {min_val}-{max_val})"
                    )
        else:
            report_lines.append("  ✅ No customizations detected")
        report_lines.append("")

        # Analyze merge type
        merge_type, affected_files, details = self.analyze_merge_type(
            new_hooks_dir
        )
        report_lines.append("MERGE ANALYSIS:")
        report_lines.append(f"  Merge Type: {merge_type}")
        report_lines.append(f"  Affected Files: {len(affected_files)}")
        for affected in affected_files:
            report_lines.append(f"    - {affected}")
        report_lines.append("")

        # Recommendations
        report_lines.append("RECOMMENDATIONS:")
        if merge_type == "NO_CHANGE":
            report_lines.append("  ✅ No merge needed - files unchanged")
        elif merge_type == "SYSTEM_ONLY":
            report_lines.append(
                "  ✅ AUTO-MERGE: System-core files changed, no customizations"
            )
        elif merge_type == "AUTO_MERGE":
            report_lines.append(
                "  ✅ AUTO-MERGE: TIER 2 files changed, no customizations"
            )
        elif merge_type == "FULL_MERGE":
            report_lines.append(
                "  ⚠️  FULL MERGE: Multiple file changes, no customizations"
            )
        elif merge_type == "MANUAL_MERGE":
            report_lines.append(
                "  🔴 MANUAL MERGE REQUIRED: Customizations detected!"
            )
            report_lines.append("     Preserve these values during merge:")
            for hook_name, fields in customizations.items():
                report_lines.append(f"       {hook_name}:")
                for field_name, field_info in fields.items():
                    report_lines.append(
                        f"         {field_name} = {field_info['current']}"
                    )

        report_lines.append("")
        return "\n".join(report_lines)

    def print_merge_report(self, new_hooks_dir: Path):
        """Print merge analysis report to stdout."""
        print(self.generate_merge_report(new_hooks_dir))


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python merge_strategy.py --analyze              # Detect customizations")
        print(
            "  python merge_strategy.py --validate             # Validate before merge"
        )
        print(
            "  python merge_strategy.py --merge <new_hooks_dir> # Analyze merge"
        )
        sys.exit(1)

    strategy = MergeStrategy()

    if sys.argv[1] == "--analyze":
        print("=== CUSTOMIZATION ANALYSIS ===\n")
        customizations = strategy.detect_customizations()
        if customizations:
            print("✅ Customizations detected:\n")
            for hook_name, fields in customizations.items():
                print(f"  {hook_name}:")
                for field_name, field_info in fields.items():
                    print(f"    {field_name}: {field_info['current']}")
        else:
            print("✅ No customizations detected")

    elif sys.argv[1] == "--validate":
        print("=== VALIDATION ===\n")
        valid, issues = strategy.validate_settings_json()
        if valid:
            print("✅ settings.json is valid")
        else:
            print("❌ Issues found:")
            for issue in issues:
                print(f"  - {issue}")

    elif sys.argv[1] == "--merge" and len(sys.argv) > 2:
        new_hooks_dir = Path(sys.argv[2])
        if not new_hooks_dir.exists():
            print(f"❌ Directory not found: {new_hooks_dir}")
            sys.exit(1)
        strategy.print_merge_report(new_hooks_dir)

    else:
        print("Unknown option")
        sys.exit(1)


if __name__ == "__main__":
    main()
