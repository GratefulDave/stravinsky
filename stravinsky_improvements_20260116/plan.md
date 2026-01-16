# Implementation Plan - Stravinsky Orchestration & Semantic Search Improvements

## Phase 1: Smart Semantic Search Auto-Index
- [ ] Task: Add index existence check and user prompt to `semantic_search()`
    - [ ] Subtask: Implement `_check_index_exists()` helper function
        ```python
        def _check_index_exists(store: CodebaseVectorStore) -> bool:
            """Check if semantic index exists for this project."""
            try:
                doc_count = store.collection.count()
                return doc_count > 0
            except Exception as e:
                logger.warning(f"Could not check index status: {e}")
                return False
        ```
    - [ ] Subtask: Add interactive Y/N prompt in `semantic_search()`
        ```python
        # In semantic_search() after store = get_store()
        if not _check_index_exists(store):
            print("\n⚠️  No semantic index found for this project.", file=sys.stderr)
            print(f"📁 Project: {project_path}", file=sys.stderr)
            print(f"🔍 Provider: {provider}", file=sys.stderr)

            # Interactive prompt with timeout
            response = input("\n🤔 Create semantic index now? [Y/n] (30s timeout): ")

            if response.lower() in ["", "y", "yes"]:
                print("\n📋 Creating semantic index...", file=sys.stderr)
                await semantic_index(project_path, provider)
                print("✅ Index created!", file=sys.stderr)

                # Auto-start file watcher
                await start_file_watcher(project_path, provider)
                print("🔄 File watcher started - index will auto-update", file=sys.stderr)
            else:
                return (
                    "❌ Index required for semantic search.\n\n"
                    f"Run: semantic_index(project_path='{project_path}', provider='{provider}')"
                )
        ```
    - [ ] Subtask: Add timeout handling for non-interactive environments
        ```python
        import signal

        def _prompt_with_timeout(prompt_text: str, timeout: int = 30) -> str:
            """Prompt user with timeout. Returns 'n' if timeout or non-interactive."""
            def timeout_handler(signum, frame):
                raise TimeoutError()

            # Check if stdin is interactive
            if not sys.stdin.isatty():
                return "n"  # Non-interactive, skip prompt

            try:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
                response = input(prompt_text)
                signal.alarm(0)  # Cancel alarm
                return response
            except (TimeoutError, EOFError):
                print("\n⏱️  Timeout - skipping index creation", file=sys.stderr)
                return "n"
        ```

- [ ] Task: Auto-start file watcher when index exists
    - [ ] Subtask: Check index exists in `semantic_search()` success path
        ```python
        # After semantic_search completes successfully
        # Check if file watcher is running
        active_watcher = get_file_watcher(project_path)

        if active_watcher is None:
            # Index exists but no watcher - start it
            print("🔄 Starting file watcher for auto-updates...", file=sys.stderr)
            await start_file_watcher(project_path, provider, debounce_seconds=2.0)
            print("✅ Watcher active - changes will auto-reindex", file=sys.stderr)
        ```
    - [ ] Subtask: Register atexit cleanup for file watchers
        ```python
        # In semantic_search.py module level
        _cleanup_registered = False

        def _register_cleanup_once():
            """Register file watcher cleanup on process exit (only once)."""
            global _cleanup_registered
            if not _cleanup_registered:
                atexit.register(_cleanup_all_watchers)
                _cleanup_registered = True

        def _cleanup_all_watchers():
            """Stop all active file watchers on exit."""
            watchers = list_file_watchers()
            for watcher_info in watchers:
                project_path = watcher_info["project_path"]
                stop_file_watcher(project_path)
                logger.info(f"Stopped file watcher for {project_path}")

        # Call in start_file_watcher()
        _register_cleanup_once()
        ```
    - [ ] Subtask: Write integration test for auto-index workflow
        ```python
        # tests/test_semantic_auto_index.py
        async def test_semantic_search_prompts_for_index(tmp_path, monkeypatch):
            """Test that semantic_search prompts when no index exists."""
            # Mock user input "y"
            monkeypatch.setattr('builtins.input', lambda _: 'y')

            # Mock semantic_index to avoid actual indexing
            index_called = False
            async def mock_index(*args, **kwargs):
                nonlocal index_called
                index_called = True

            monkeypatch.setattr('mcp_bridge.tools.semantic_search.semantic_index', mock_index)

            # Run semantic_search
            result = await semantic_search("test query", project_path=str(tmp_path))

            # Verify index was created
            assert index_called
        ```

- [ ] Task: Agent Manual Verification - Phase 1 Smart Semantic Search
    - [ ] Subtask: Human tester runs `semantic_search("find auth logic")` on fresh project
    - [ ] Subtask: Verify Y/N prompt appears when no index exists
    - [ ] Subtask: Verify file watcher auto-starts and survives Claude Code restart

## Phase 2: Reinforced TODO Enforcement
- [ ] Task: Strengthen `todo_enforcer.py` with verification protocol
    - [ ] Subtask: Add evidence extraction from agent output
        ```python
        # In todo_enforcer.py
        def _extract_evidence(output: str) -> dict[str, list[str]]:
            """Extract evidence references (file paths, URLs) from agent output."""
            evidence = {
                "files": [],
                "urls": [],
                "commands": []
            }

            # File path pattern: src/auth.ts:45 or /path/to/file.py
            file_pattern = r'(?:^|[\s\(])([\w/\.-]+\.(py|ts|js|tsx|jsx|go|rs|java|c|cpp))(?::(\d+))?'
            for match in re.finditer(file_pattern, output):
                file_path = match.group(1)
                line_num = match.group(3)
                ref = f"{file_path}:{line_num}" if line_num else file_path
                evidence["files"].append(ref)

            # URL pattern
            url_pattern = r'https?://[^\s\)]+'
            evidence["urls"] = re.findall(url_pattern, output)

            return evidence
        ```
    - [ ] Subtask: Implement verification for file-based claims
        ```python
        async def _verify_file_claim(claim: str, file_path: str) -> bool:
            """Verify a file exists and contains expected content."""
            try:
                # Read file using MCP Read tool
                content = await mcp_read_file(file_path)

                # Check if claim keywords appear in file
                claim_keywords = claim.lower().split()
                content_lower = content.lower()

                # At least 50% of claim keywords must appear
                matches = sum(1 for kw in claim_keywords if kw in content_lower)
                return matches >= len(claim_keywords) * 0.5

            except FileNotFoundError:
                return False
            except Exception as e:
                logger.warning(f"Could not verify file claim: {e}")
                return False
        ```
    - [ ] Subtask: Update TODO_CONTINUATION_REMINDER with evidence requirement
        ```python
        TODO_CONTINUATION_REMINDER = """
        [SYSTEM REMINDER - TODO CONTINUATION & VERIFICATION]

        You have pending todos that are NOT yet completed. You MUST continue working.

        **Pending Todos:**
        {pending_todos}

        **CRITICAL RULES:**
        1. You CANNOT mark a todo completed without CONCRETE EVIDENCE
        2. Evidence = file paths with line numbers (e.g., src/auth.ts:45-67)
        3. Vague claims like "I created the file" will be REJECTED
        4. Each completed todo MUST include: `✅ [Todo] - Evidence: path/to/file.py:123`
        5. If you cannot provide evidence, the todo is NOT complete - keep working

        **Example GOOD completion:**
        ✅ Create auth validation → Evidence: src/auth.ts:45-67 (validateJWT function)

        **Example BAD completion (will be REJECTED):**
        ✅ Create auth validation → I created the validation logic

        CONTINUE WORKING NOW with evidence-backed completions.
        """
        ```

- [ ] Task: Add "Subagents LIE" verification protocol
    - [ ] Subtask: Create `_verify_agent_claims()` function
        ```python
        async def _verify_agent_claims(
            agent_output: str,
            expected_outcomes: list[str]
        ) -> dict[str, bool]:
            """
            Verify agent claims against actual evidence.

            Returns:
                Dict mapping each expected outcome to verification status
            """
            evidence = _extract_evidence(agent_output)
            verifications = {}

            for outcome in expected_outcomes:
                # Check if outcome mentions a file
                if any(file_ref in outcome for file_ref in evidence["files"]):
                    # Verify file exists
                    file_path = evidence["files"][0].split(":")[0]
                    verified = await _verify_file_claim(outcome, file_path)
                    verifications[outcome] = verified
                else:
                    # No file evidence - cannot verify
                    verifications[outcome] = False

            return verifications
        ```
    - [ ] Subtask: Inject verification results into next prompt
        ```python
        # After agent completes
        verifications = await _verify_agent_claims(agent_output, expected_outcomes)

        failed = [outcome for outcome, verified in verifications.items() if not verified]

        if failed:
            verification_warning = f"""
            ⚠️ VERIFICATION FAILED for {len(failed)} claims:
            {chr(10).join(f"- {claim}" for claim in failed)}

            You claimed these were complete but provided NO EVIDENCE.
            Re-do these tasks with file paths and line numbers.
            """
            # Inject into next prompt
            params["prompt"] += "\n\n" + verification_warning
        ```
    - [ ] Subtask: Write test for verification rejection
        ```python
        async def test_todo_enforcer_rejects_unverified_claims():
            """Test that claims without evidence are rejected."""
            output = "I created the auth file"  # No file path
            expected = ["Create src/auth.ts"]

            verifications = await _verify_agent_claims(output, expected)

            assert verifications["Create src/auth.ts"] == False
        ```

- [ ] Task: Agent Manual Verification - Phase 2 TODO Enforcement
    - [ ] Subtask: Human tester creates todos with /strav command
    - [ ] Subtask: Verify agent cannot skip todos without evidence
    - [ ] Subtask: Verify verification failure message appears for vague claims

## Phase 3: Clean Output Formatting
- [ ] Task: Add clean output mode to `agent_spawn()`
    - [ ] Subtask: Create output formatter with ANSI colors
        ```python
        # In mcp_bridge/tools/agent_manager.py
        from enum import Enum

        class OutputMode(Enum):
            CLEAN = "clean"      # ✓ agent:model → task_id
            VERBOSE = "verbose"  # Current behavior (full prompt)
            SILENT = "silent"    # task_id only

        def format_spawn_output(
            mode: OutputMode,
            agent_type: str,
            model: str,
            description: str,
            task_id: str
        ) -> str:
            """Format agent spawn output based on mode."""
            if mode == OutputMode.SILENT:
                return task_id

            elif mode == OutputMode.CLEAN:
                GREEN = "\033[92m"
                CYAN = "\033[96m"
                YELLOW = "\033[93m"
                RESET = "\033[0m"

                return f"{GREEN}✓{RESET} {CYAN}{agent_type}{RESET}:{YELLOW}{model}{RESET} → {task_id}"

            else:  # VERBOSE
                return f"🟢 {agent_type}:{model}('{description}') ⏳\ntask_id={task_id}"

        # Global config (can be set via env var)
        DEFAULT_OUTPUT_MODE = OutputMode.CLEAN
        ```
    - [ ] Subtask: Add progress notification thread
        ```python
        def _start_progress_monitor(task_id: str, agent_type: str):
            """Background thread for periodic progress updates."""
            def monitor():
                start_time = time.time()
                while True:
                    time.sleep(10)  # Update every 10 seconds

                    # Check if still running
                    status = check_agent_status(task_id)
                    if status in ["completed", "failed", "cancelled"]:
                        break

                    elapsed = int(time.time() - start_time)
                    YELLOW = "\033[93m"
                    CYAN = "\033[96m"
                    RESET = "\033[0m"

                    print(
                        f"{YELLOW}⏳{RESET} {CYAN}{task_id}{RESET} running ({elapsed}s)...",
                        file=sys.stderr
                    )

            thread = threading.Thread(target=monitor, daemon=True)
            thread.start()
        ```
    - [ ] Subtask: Update `agent_spawn()` to use new formatter
        ```python
        # In agent_spawn() return statement
        output = format_spawn_output(
            DEFAULT_OUTPUT_MODE,
            agent_type,
            model,
            description,
            task_id
        )

        # Start progress monitor (if not blocking)
        if not blocking:
            _start_progress_monitor(task_id, agent_type)

        return output
        ```

- [ ] Task: Add completion notifications in `agent_output()`
    - [ ] Subtask: Extract one-sentence summary from agent result
        ```python
        def _extract_summary(agent_output: str, max_length: int = 80) -> str:
            """Extract a one-sentence summary from agent output."""
            # Look for explicit summary markers
            if "<summary>" in agent_output:
                match = re.search(r'<summary>(.*?)</summary>', agent_output, re.DOTALL)
                if match:
                    return match.group(1).strip()[:max_length]

            # Look for first sentence
            sentences = re.split(r'[.!?]\s+', agent_output)
            if sentences:
                first = sentences[0].strip()
                if len(first) <= max_length:
                    return first
                return first[:max_length-3] + "..."

            return "No summary available"
        ```
    - [ ] Subtask: Print completion notification
        ```python
        # In agent_output() when status == "completed"
        duration = result.get("duration", 0)
        summary = _extract_summary(result.get("output", ""), max_length=80)

        GREEN = "\033[92m"
        CYAN = "\033[96m"
        RESET = "\033[0m"

        print(
            f"{GREEN}✅{RESET} {CYAN}{task_id}{RESET} ({duration}s) - {summary}",
            file=sys.stderr
        )
        ```
    - [ ] Subtask: Add failure notification with error details
        ```python
        # In agent_output() when status == "failed"
        error = result.get("error", "Unknown error")

        RED = "\033[91m"
        CYAN = "\033[96m"
        RESET = "\033[0m"

        print(
            f"{RED}❌{RESET} {CYAN}{task_id}{RESET} failed - {error}",
            file=sys.stderr
        )
        ```

- [ ] Task: Agent Manual Verification - Phase 3 Clean Output
    - [ ] Subtask: Human tester spawns multiple agents in parallel
    - [ ] Subtask: Verify clean format: `✓ agent:model → task_id` (under 100 chars)
    - [ ] Subtask: Verify progress updates appear every 10s: `⏳ agent_id (Xs)...`

## Phase 4: Delegation Enforcement
- [ ] Task: Add mandatory parameters to `agent_spawn()`
    - [ ] Subtask: Update function signature with required params
        ```python
        # In mcp_bridge/tools/agent_manager.py
        async def agent_spawn(
            agent_type: str,
            prompt: str,
            # NEW REQUIRED PARAMETERS
            delegation_reason: str,      # WHY this agent
            expected_outcome: str,        # WHAT it should produce
            required_tools: list[str],    # WHICH tools it needs
            # Optional parameters
            description: str | None = None,
            blocking: bool = False,
            success_criteria: str | None = None,
            fallback_plan: str | None = None,
            forbidden_actions: list[str] | None = None,
            model: str | None = None,
            timeout: int = 300
        ) -> str:
            """
            Spawn a background agent with mandatory delegation protocol.

            Args:
                delegation_reason: Why this agent (e.g., "explore specializes in code search")
                expected_outcome: What agent should produce (e.g., "List of auth files with lines")
                required_tools: Tools agent will use (e.g., ["semantic_search", "Read"])
                success_criteria: How to verify success (e.g., "Found 3+ auth files")
                fallback_plan: What to do if agent fails (e.g., "Use grep as fallback")
                forbidden_actions: What agent must NOT do (e.g., ["Do not modify files"])
            """
            # Validate required parameters
            if not delegation_reason:
                raise ValueError(
                    "delegation_reason is REQUIRED. "
                    "Explain WHY you're delegating to this agent."
                )

            if not expected_outcome:
                raise ValueError(
                    "expected_outcome is REQUIRED. "
                    "Specify WHAT the agent should produce."
                )

            if not required_tools:
                raise ValueError(
                    "required_tools is REQUIRED. "
                    "List WHICH tools the agent will use."
                )

            # ... rest of implementation
        ```
    - [ ] Subtask: Validate tools are available for agent
        ```python
        # Tool availability matrix
        AGENT_TOOLS = {
            "explore": [
                "Read", "Grep", "Glob",
                "mcp__ast-grep__find_code",
                "mcp__grep-app__searchCode",
                "mcp__stravinsky__semantic_search",
                "mcp__stravinsky__lsp_diagnostics",
            ],
            "dewey": [
                "WebSearch", "WebFetch",
                "mcp__grep-app__searchCode",
            ],
            "delphi": [
                "Read", "Grep", "Glob",
                "mcp__ast-grep__find_code",
                "mcp__stravinsky__lsp_diagnostics",
            ],
        }

        def validate_agent_tools(agent_type: str, required_tools: list[str]):
            """Validate requested tools are available for agent."""
            available = AGENT_TOOLS.get(agent_type, [])
            missing = set(required_tools) - set(available)

            if missing:
                raise ValueError(
                    f"Agent '{agent_type}' does not have access to: {missing}\n"
                    f"Available tools: {available}"
                )
        ```
    - [ ] Subtask: Update stravinsky.md with delegation protocol
        ```markdown
        ## Delegation Protocol (MANDATORY)

        When calling agent_spawn, you MUST provide all 7 sections:

        ```python
        agent_spawn(
            agent_type="explore",

            # Section 1: Task Definition
            prompt="Find authentication implementation",

            # Section 2: Delegation Reason
            delegation_reason="explore specializes in codebase search with semantic and AST tools",

            # Section 3: Expected Outcome
            expected_outcome="List of files with auth code, line numbers, and pattern descriptions",

            # Section 4: Required Tools
            required_tools=["semantic_search", "ast-grep", "Read"],

            # Section 5: Success Criteria
            success_criteria="Found at least 3 auth-related files with concrete evidence",

            # Section 6: Failure Handling
            fallback_plan="If semantic search fails, use grep for 'authenticate' keyword",

            # Section 7: Forbidden Actions
            forbidden_actions=["Do not modify files", "Do not run tests"]
        )
        ```

        **Calls without all 7 sections will FAIL with validation error.**
        ```

- [ ] Task: Implement agent type blocking (prevent recursion)
    - [ ] Subtask: Define orchestrator vs worker agents
        ```python
        # Agent type classifications
        ORCHESTRATOR_AGENTS = [
            "stravinsky",
            "research-lead",
            "implementation-lead"
        ]

        WORKER_AGENTS = [
            "explore",
            "dewey",
            "delphi",
            "frontend",
            "debugger",
            "code-reviewer",
            "momus",
            "comment_checker"
        ]
        ```
    - [ ] Subtask: Add blocking validation in agent_spawn
        ```python
        def validate_agent_hierarchy(caller_agent: str, target_agent: str):
            """Prevent invalid agent delegation patterns."""
            # Rule 1: Workers cannot spawn orchestrators
            if caller_agent in WORKER_AGENTS and target_agent in ORCHESTRATOR_AGENTS:
                raise ValueError(
                    f"Worker agent '{caller_agent}' cannot spawn orchestrator '{target_agent}'. "
                    f"Only orchestrators can spawn other agents."
                )

            # Rule 2: Workers cannot spawn other workers (prevents lateral delegation)
            if caller_agent in WORKER_AGENTS and target_agent in WORKER_AGENTS:
                raise ValueError(
                    f"Worker agent '{caller_agent}' cannot spawn another worker '{target_agent}'. "
                    f"Workers must complete work themselves or fail."
                )

            # Orchestrators can spawn any worker (allowed)
            if caller_agent in ORCHESTRATOR_AGENTS and target_agent in WORKER_AGENTS:
                return  # Valid delegation

        # In agent_spawn()
        caller_agent = _get_current_agent_context()
        validate_agent_hierarchy(caller_agent, agent_type)
        ```
    - [ ] Subtask: Write tests for blocking rules
        ```python
        def test_worker_cannot_spawn_orchestrator():
            """Workers blocked from spawning orchestrators."""
            with pytest.raises(ValueError, match="cannot spawn orchestrator"):
                agent_spawn(
                    agent_type="stravinsky",
                    caller_agent="explore",  # Worker trying to spawn orchestrator
                    # ... other params
                )

        def test_worker_cannot_spawn_worker():
            """Workers blocked from lateral delegation."""
            with pytest.raises(ValueError, match="cannot spawn another worker"):
                agent_spawn(
                    agent_type="dewey",
                    caller_agent="explore",  # Worker trying to spawn worker
                    # ... other params
                )
        ```

- [ ] Task: Agent Manual Verification - Phase 4 Delegation
    - [ ] Subtask: Human tester tries agent_spawn without delegation_reason (should fail)
    - [ ] Subtask: Verify validation error message is clear and actionable
    - [ ] Subtask: Verify worker agents cannot spawn orchestrators

## Phase 5: New Quality Agents
- [ ] Task: Create Momus quality gate agent
    - [ ] Subtask: Write `.claude/agents/momus.md` definition
        ```markdown
        ---
        agent_type: momus
        model: claude-sonnet-4.5
        tools:
          - Read
          - Grep
          - Glob
          - mcp__stravinsky__lsp_diagnostics
          - mcp__ast-grep__find_code
        ---

        # Momus - Quality Gate Agent

        You are Momus, the quality gate. Your role is to validate completed work before marking it done.

        ## Validation Checklist

        For code changes:
        - [ ] Tests exist and pass (or test plan documented if no tests yet)
        - [ ] No linting errors (check with lsp_diagnostics)
        - [ ] No introduced security vulnerabilities
        - [ ] Follows codebase patterns (consistent style)
        - [ ] Breaking changes documented

        For research:
        - [ ] Sources cited with URLs
        - [ ] Claims backed by evidence (file paths, line numbers)
        - [ ] Alternative solutions considered

        ## Output Format (MANDATORY)

        ```json
        {
          "status": "approved" | "rejected",
          "issues": ["list of blocking issues that must be fixed"],
          "suggestions": ["non-blocking improvements"]
        }
        ```

        **NEVER approve without verification. Run lsp_diagnostics, read files, check tests.**

        ## Evidence Requirements

        Every validation claim needs concrete evidence:
        - "Tests pass" → Show test output or file paths to test files
        - "No linting errors" → Show lsp_diagnostics output
        - "Follows patterns" → Reference similar code with file:line

        **Example GOOD validation:**
        ```json
        {
          "status": "approved",
          "issues": [],
          "suggestions": ["Consider adding error handling in src/auth.ts:67"]
        }
        ```

        **Example BAD validation (will be REJECTED):**
        ```json
        {
          "status": "approved",
          "issues": [],
          "suggestions": []
        }
        ```
        (Missing: Where did you check? What tests? What files?)
        ```
    - [ ] Subtask: Register momus in AGENT_TOOLS matrix
        ```python
        AGENT_TOOLS["momus"] = [
            "Read",
            "Grep",
            "Glob",
            "mcp__stravinsky__lsp_diagnostics",
            "mcp__ast-grep__find_code"
        ]
        ```
    - [ ] Subtask: Write integration test for momus validation
        ```python
        async def test_momus_rejects_code_without_tests():
            """Momus should reject code changes that have no tests."""
            # Spawn momus to validate a code change
            result = await agent_spawn(
                agent_type="momus",
                prompt="Validate src/auth.ts changes",
                delegation_reason="momus validates quality before completion",
                expected_outcome="Approval or rejection with issues list",
                required_tools=["Read", "lsp_diagnostics"]
            )

            # Verify momus ran lsp_diagnostics and checked for tests
            output = await agent_output(result)
            assert "lsp_diagnostics" in output or "tests" in output.lower()
        ```

- [ ] Task: Create Comment-Checker agent (user requested)
    - [ ] Subtask: Write `.claude/agents/comment_checker.md` definition
        ```markdown
        ---
        agent_type: comment_checker
        model: claude-sonnet-4.5
        tools:
          - Read
          - Grep
          - Glob
          - mcp__ast-grep__find_code
          - Write
        ---

        # Comment-Checker Agent

        You validate code documentation quality and add missing comments where needed.

        ## Documentation Criteria

        1. **Public APIs** - Must have docstrings/JSDoc
        2. **Complex logic** - Needs inline explanation
        3. **Magic numbers** - Require named constants with comments
        4. **TODOs** - Must have context and owner
        5. **Exported functions** - Must document params and return type

        ## Process

        1. Use ast-grep to find functions/classes without docstrings:
           ```python
           # Find Python functions without docstrings
           pattern = "def $FUNC($$$):\n    $$$"
           ```

        2. Read surrounding code to understand purpose

        3. Generate appropriate comments/docstrings following project style

        4. Use Write tool to add comments (or report findings if no Write access)

        ## Output Format (MANDATORY)

        ```json
        {
          "files_updated": ["path/to/file.py"],
          "comments_added": 5,
          "issues": [
            "src/auth.ts:45 - Complex crypto logic undocumented",
            "src/db.py:123 - Magic number 3600 needs constant"
          ],
          "recommendations": [
            "Consider adding module-level docstring to src/utils.py"
          ]
        }
        ```

        ## Examples

        **GOOD comment:**
        ```python
        def validate_jwt(token: str) -> dict:
            \"\"\"
            Validate JWT token and extract payload.

            Args:
                token: JWT token string (Bearer format)

            Returns:
                Decoded payload dict if valid

            Raises:
                ValueError: If token is invalid or expired
            \"\"\"
        ```

        **BAD comment (too vague):**
        ```python
        def validate_jwt(token: str) -> dict:
            \"\"\"Validates a token.\"\"\"
        ```
        ```
    - [ ] Subtask: Register comment_checker in AGENT_TOOLS
        ```python
        AGENT_TOOLS["comment_checker"] = [
            "Read",
            "Grep",
            "Glob",
            "mcp__ast-grep__find_code",
            "Write"  # Can add comments
        ]
        ```
    - [ ] Subtask: Write test for comment detection
        ```python
        async def test_comment_checker_finds_undocumented_functions():
            """Comment-checker should find functions without docstrings."""
            # Create test file without docstrings
            test_file = tmp_path / "test.py"
            test_file.write_text(
                "def calculate(x, y):\n"
                "    return x * y + 42\n"
            )

            # Run comment_checker
            result = await agent_spawn(
                agent_type="comment_checker",
                prompt=f"Check {test_file}",
                delegation_reason="comment_checker finds undocumented code",
                expected_outcome="List of functions needing docs",
                required_tools=["ast-grep", "Read"]
            )

            output = await agent_output(result)
            assert "calculate" in output
            assert "undocumented" in output.lower()
        ```

- [ ] Task: Agent Manual Verification - Phase 5 New Agents
    - [ ] Subtask: Human tester spawns momus to validate a code change
    - [ ] Subtask: Verify momus runs lsp_diagnostics and provides evidence
    - [ ] Subtask: Human tester spawns comment_checker on undocumented code
    - [ ] Subtask: Verify comment_checker identifies missing docstrings

## Implementation Summary

### Files Created
1. `.claude/agents/momus.md` - Quality gate agent definition
2. `.claude/agents/comment_checker.md` - Documentation validator
3. `tests/test_semantic_auto_index.py` - Auto-index tests
4. `tests/test_delegation_enforcement.py` - Delegation validation tests

### Files Modified
1. `mcp_bridge/tools/semantic_search.py` - Add auto-index check + cleanup
2. `mcp_bridge/hooks/todo_enforcer.py` - Add verification protocol
3. `mcp_bridge/tools/agent_manager.py` - Add delegation enforcement + clean output
4. `.claude/agents/stravinsky.md` - Add 7-section delegation protocol
5. `mcp_bridge/server.py` - Register momus and comment_checker tools

### Key Improvements Summary
- ✅ Semantic search auto-detects missing index, prompts Y/N
- ✅ File watcher auto-starts when index exists
- ✅ File watcher auto-stops on Claude Code exit (atexit)
- ✅ TODO enforcer rejects claims without evidence (file:line format)
- ✅ Agent spawn outputs clean: `✓ agent:model → task_id`
- ✅ Progress notifications every 10s: `⏳ agent_id (Xs)...`
- ✅ Delegation requires 7 mandatory sections
- ✅ Worker agents blocked from spawning orchestrators
- ✅ Momus quality gate agent validates before completion
- ✅ Comment-Checker finds undocumented code

## Post-Implementation Checklist
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual verification completed for all 5 phases
- [ ] Documentation updated (README.md, ARCHITECTURE.md)
- [ ] Version bumped in pyproject.toml
- [ ] Deployed to PyPI
- [ ] uvx cache cleared (force fresh fetch)
