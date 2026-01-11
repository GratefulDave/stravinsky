"""
Keyword Detector Hook.

Detects trigger keywords (ultrawork, search, analyze) in user prompts
and injects corresponding mode activation tags.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

ULTRAWORK_MODE = """<ultrawork-mode>
[CODE RED] Maximum precision required. Ultrathink before acting.

YOU MUST LEVERAGE ALL AVAILABLE AGENTS TO THEIR FULLEST POTENTIAL.
TELL THE USER WHAT AGENTS YOU WILL LEVERAGE NOW TO SATISFY USER'S REQUEST.

## AGENT UTILIZATION PRINCIPLES (by capability, not by name)
- **Codebase Exploration**: Spawn exploration agents using BACKGROUND TASKS for file patterns, internal implementations, project structure
- **Documentation & References**: Use dewey agents via BACKGROUND TASKS for API references, examples, external library docs
- **Planning & Strategy**: NEVER plan yourself - ALWAYS spawn a dedicated planning agent for work breakdown
- **High-IQ Reasoning**: Leverage delphi for architecture decisions, code review, strategic planning
- **Frontend/UI Tasks**: Delegate to frontend-ui-ux-engineer for design and implementation

## EXECUTION RULES
- **TODO**: Track EVERY step. Mark complete IMMEDIATELY after each.
- **PARALLEL**: Fire independent agent calls simultaneously via background_task - NEVER wait sequentially.
- **BACKGROUND FUWT**: Use background_task for exploration/research agents (10+ concurrent if needed).
- **VERIFY**: Re-read request after completion. Check ALL requirements met before reporting done.
- **DELEGATE**: Don't do everything yourself - orchestrate specialized agents for their strengths.

## WORKFLOW
1. Analyze the request and identify required capabilities
2. Spawn exploration/dewey agents via background_task in PARALLEL (10+ if needed)
3. Always Use Plan agent with gathered context to create detailed work breakdown
4. Execute with continuous verification against original requirements

## TDD (if test infrastructure exists)

1. Write spec (requirements)
2. Write tests (failing)
3. RED: tests fail
4. Implement minimal code
5. GREEN: tests pass
6. Refactor if needed (must stay green)
7. Next feature, repeat

## ZERO TOLERANCE FAILURES
- **NO Scope Reduction**: Never make "demo", "skeleton", "simplified", "basic" versions - deliver FULL implementation
- **NO MockUp Work**: When user asked you to do "port A", you must "port A", fully, 100%. No Extra feature, No reduced feature, no mock data, fully working 100% port.
- **NO Partial Completion**: Never stop at 60-80% saying "you can extend this..." - finish 100%
- **NO Assumed Shortcuts**: Never skip requirements you deem "optional" or "can be added later"
- **NO Premature Stopping**: Never declare done until ALL TODOs are completed and verified
- **NO TEST DELETION**: Never delete or skip failing tests to make the build pass. Fix the code, not the tests.

THE USER ASKED FOR X. DELIVER EXACTLY X. NOT A SUBSET. NOT A DEMO. NOT A STARTING POINT.

</ultrawork-mode>

---
"""

SEARCH_MODE = """[search-mode]
MAXIMIZE SEARCH EFFORT. Launch multiple background agents IN PARALLEL:
- explore agents (codebase patterns, file structures, ast-grep)
- dewey agents (remote repos, official docs, GitHub examples)
Plus direct tools: Grep, ripgrep (rg), ast-grep (sg)
NEVER stop at first result - be exhaustive.
"""

ANALYZE_MODE = """[analyze-mode]
ANALYSIS MODE. Gather context before diving deep:

CONTEXT GATHERING (parallel):
- 1-2 explore agents (codebase patterns, implementations)
- 1-2 dewey agents (if external library involved)
- Direct tools: Grep, AST-grep, LSP for targeted searches

IF COMPLEX (architecture, multi-system, debugging after 2+ failures):
- Consult delphi for strategic guidance

SYNTHESIZE findings before proceeding.
"""

ULTRATHINK_MODE = """[ultrathink-mode]
ENGAGE MAXIMUM REASONING CAPACITY.

Extended thinking mode activated with 32k token thinking budget.
This enables exhaustive deep reasoning and multi-dimensional analysis.

## REASONING PRINCIPLES
- **Deep Analysis**: Consider edge cases, security implications, performance impacts
- **Multi-Perspective**: Analyze from user, developer, system, and security viewpoints
- **Strategic Planning**: Consult delphi agent for architecture decisions and hard problems
- **Root Cause**: Don't treat symptoms - identify and address underlying causes
- **Risk Assessment**: Evaluate trade-offs, failure modes, and mitigation strategies

## THINKING WORKFLOW
1. Problem decomposition into atomic components
2. Parallel exploration of solution space (spawn agents for research)
3. Consult delphi for strategic guidance on complex decisions
4. Multi-dimensional trade-off analysis
5. Solution synthesis with verification plan

## VERIFICATION
- Test assumptions against reality
- Challenge your own reasoning
- Seek disconfirming evidence
- Consider second-order effects

Use delphi agent for strategic consultation on architecture, debugging, and complex trade-offs.
"""

KEYWORD_PATTERNS = {
    r"\bultrawork\b": ULTRAWORK_MODE,
    r"\buw\b": ULTRAWORK_MODE,
    r"\bultrathink\b": ULTRATHINK_MODE,
    r"\bsearch\b": SEARCH_MODE,
    r"\banalyze\b": ANALYZE_MODE,
    r"\banalysis\b": ANALYZE_MODE,
}


async def keyword_detector_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Pre-model invoke hook that detects keywords and injects mode tags.
    """
    prompt = params.get("prompt", "")
    prompt_lower = prompt.lower()

    injections = []
    matched_modes = set()

    for pattern, mode_tag in KEYWORD_PATTERNS.items():
        if re.search(pattern, prompt_lower):
            mode_id = id(mode_tag)
            if mode_id not in matched_modes:
                matched_modes.add(mode_id)
                injections.append(mode_tag)
                logger.info(f"[KeywordDetector] Matched pattern '{pattern}', injecting mode tag")

    if injections:
        injection_block = "\n".join(injections)
        modified_prompt = prompt + "\n\n" + injection_block
        params["prompt"] = modified_prompt
        return params

    return None
