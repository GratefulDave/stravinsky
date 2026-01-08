# Manifest Quick Reference

## Files

| File | Purpose | Records |
|------|---------|---------|
| `hooks_manifest.json` | Official hook versions and metadata | 32 hooks |
| `skills_manifest.json` | Slash command versions and metadata | 16 skills |
| `MANIFEST_SCHEMA.md` | Detailed schema documentation | Reference |
| `README.md` | Integration guide | Guide |

## Hooks by Priority

### Critical (2)
- `manager.py` - Central hook management
- `stravinsky_mode.py` - Hard blocking of direct tools

### High (11)
- `parallel_execution.py` - Pre-emptive parallel enforcement
- `todo_delegation.py` - TodoWrite delegation enforcer
- `context.py` - Auto-inject project context
- `rules_injector.py` - Inject .claude/rules/
- `pre_compact.py` - Preserve context before compaction
- `preemptive_compaction.py` - Proactive context compaction
- `parallel_enforcer.py` - Enforce parallelization
- `keyword_detector.py` - Detect ULTRATHINK/ULTRAWORK
- `git_noninteractive.py` - Non-interactive git
- `session_recovery.py` - Handle session errors
- `__init__.py` - Package initialization

### Medium (12)
- `context_monitor.py` - Monitor context window
- `directory_context.py` - Add directory structure
- `tool_messaging.py` - User-friendly tool messages
- `truncator.py` - Prevent token overflow
- `notification_hook.py` - Agent spawn notifications
- `subagent_stop.py` - Agent completion handling
- `empty_message_sanitizer.py` - Sanitize empty responses
- `comment_checker.py` - Validate documentation
- `auto_slash_command.py` - Auto-invoke skills
- `budget_optimizer.py` - Optimize token usage
- `compaction.py` - Trigger compaction
- `task_validator.py` - Validate task calls

### Low (7)
- `edit_recovery.py` - Suggest recovery for Edit failures
- `agent_reminder.py` - Remind about agents
- `session_idle.py` - Detect session idle
- `session_notifier.py` - Notify session events
- `tmux_manager.py` - tmux session integration

## Hooks by Type

### PreToolUse (2)
- `stravinsky_mode.py` - Hard blocks direct tools
- `comment_checker.py` - Validate comments
- `git_noninteractive.py` - Non-interactive git

### PostToolUse (12)
- `tool_messaging.py` - Tool result messaging
- `edit_recovery.py` - Edit failure recovery
- `truncator.py` - Truncate long responses
- `empty_message_sanitizer.py` - Sanitize empty messages
- `preemptive_compaction.py` - Proactive compaction
- `parallel_enforcer.py` - Enforce parallelization
- `agent_reminder.py` - Agent suggestions
- `compaction.py` - Trigger compaction
- `task_validator.py` - Validate tasks
- `context_monitor.py` - Monitor context
- `session_notifier.py` - Session events
- `session_recovery.py` - Session error recovery

### UserPromptSubmit (6)
- `context.py` - Auto-inject context
- `todo_continuation.py` - Remind about todos
- `todo_enforcer.py` - Enforce todo consistency
- `directory_context.py` - Add directory info
- `rules_injector.py` - Inject rules
- `keyword_detector.py` - Detect keywords
- `auto_slash_command.py` - Auto-invoke skills

### PreCompact (1)
- `pre_compact.py` - Preserve critical context

### Notification (1)
- `notification_hook.py` - Agent notifications

### SubagentStop (1)
- `subagent_stop.py` - Agent completion

## Skills by Category

### Core (4)
- `/strav` - Task orchestration
- `/strav:loop` - Continuation loops
- `/strav:cancel-loop` - Cancel loops
- `/version` - Diagnostic info

### Implementation (4)
- `/commit` - Git commit orchestration
- `/review` - Code quality review
- `/verify` - Test/deploy verification
- `/publish` - PyPI deployment

### Research (7)
- `/dewey` - Documentation research
- `/index` - Semantic search index
- `/str:index` - Detailed indexing
- `/str:search` - Semantic search
- `/str:start_filewatch` - Auto-indexing
- `/str:stop_filewatch` - Stop auto-index
- `/str:stats` - Index statistics

### Architecture (1)
- `/delphi` - Strategic advisor

## Skills by Agent

### stravinsky (4)
- `/strav`, `/strav:loop`, `/strav:cancel-loop`, `/version`

### implementation_lead (3)
- `/commit`, `/verify`, `/publish`

### code_reviewer (1)
- `/review`

### delphi (1)
- `/delphi`

### dewey (1)
- `/dewey`

### explore (6)
- `/index`, `/str:index`, `/str:search`, `/str:start_filewatch`, `/str:stop_filewatch`, `/str:stats`

## Required Hooks (9)

These cannot be disabled:
1. `__init__.py`
2. `manager.py`
3. `parallel_execution.py`
4. `stravinsky_mode.py`
5. `todo_delegation.py`
6. `context.py`
7. `rules_injector.py`
8. `pre_compact.py`
9. `parallel_enforcer.py`

## Skills Requiring OAuth

These need authentication setup:
- `/delphi` - Requires OpenAI (ChatGPT Plus/Pro)
- `/dewey` - Requires Gemini or OpenAI
- `/str:search` (optional) - Can use cloud providers

Setup with:
```bash
stravinsky-auth login gemini    # Google/Gemini
stravinsky-auth login openai    # OpenAI/ChatGPT
```

## Common Checksum Operations

### Generate for single file
```bash
sha256sum mcp_bridge/hooks/hook_name.py | awk '{print substr($1,1,12)}'
```

### Verify file unchanged
```bash
# Compare current with manifest
current=$(sha256sum FILE | awk '{print substr($1,1,12)}')
expected=$(jq -r '.hooks.HOOK.checksum' hooks_manifest.json)
[ "$current" = "$expected" ] && echo "OK" || echo "MODIFIED"
```

### Generate all checksums
```bash
for f in mcp_bridge/hooks/*.py; do
  name=$(basename "$f" .py)
  sha=$(sha256sum "$f" | awk '{print substr($1,1,12)}')
  echo "    \"$name\": \"$sha\","
done
```

## Field Reference

### All Entries Have
- `description` - What it does
- `checksum` - SHA-256 (first 12 chars)
- `lines_of_code` - Approximate LOC
- `updatable` - Can be auto-updated
- `priority` - critical|high|medium|low
- `version_first_added` - Stravinsky version

### Hooks Additional
- `version` - Semantic version
- `source` - File path
- `hook_type` - Claude Code hook type
- `required` - Critical vs optional
- `dependencies` - Other files needed

### Skills Additional
- `file_path` - Relative path
- `category` - core|research|implementation|architecture
- `agent_type` - Which agent spawns
- `blocking` - Blocks vs async
- `requires_auth` - Needs OAuth setup

## JSON Query Examples

### List all critical hooks
```bash
jq '.hooks | to_entries[] | select(.value.priority == "critical") | .key' hooks_manifest.json
```

### Count hooks by priority
```bash
jq '.hooks | to_entries[] | .value.priority' hooks_manifest.json | sort | uniq -c
```

### Get all required hooks
```bash
jq '.hooks | to_entries[] | select(.value.required) | .key' hooks_manifest.json
```

### List async skills
```bash
jq '.skills | to_entries[] | select(.value.blocking == false) | .key' skills_manifest.json
```

### Get hooks needing specific dependency
```bash
jq '.hooks | to_entries[] | select(.value.dependencies[] == "manager.py") | .key' hooks_manifest.json
```

## Statistics

### Hooks
- Total: 32
- Required: 9 (28%)
- Optional: 23 (72%)
- Critical: 2, High: 11, Medium: 12, Low: 7
- All updatable: true

### Skills
- Total: 16
- Blocking: 6 (38%)
- Async: 10 (62%)
- Requiring auth: 3 (19%)
- Categories: core (4), implementation (4), research (7), architecture (1)

## Version Info

- Manifest Schema: 1.0.0
- Generated For: 0.3.9
- Hook Package Version: 0.2.63

## Integration Points

### update_manager.py
- Loads manifest to determine update strategy
- Verifies checksums before updating
- Skips user-customized files
- Respects priority levels

### install_hooks.py
- Installs hooks from manifest
- Validates dependencies
- Sets file permissions
- Registers with Claude Code

### hooks/manager.py
- Executes hooks in defined order
- Manages hook lifecycle
- Handles errors and retries

### skills
- Discovered from .claude/commands/**/*.md
- Registered at startup
- Invoked via /skill_name syntax

## Troubleshooting Quick Links

- **Invalid JSON?** → Check syntax with `python -m json.tool`
- **Checksums wrong?** → Regenerate with `scripts/generate_manifests.py`
- **Missing hooks?** → List both manifest and filesystem
- **Update fails?** → Check permissions and dependencies
- **Skills not showing?** → Run skill_list()

See **MANIFEST_SCHEMA.md** for complete documentation.
