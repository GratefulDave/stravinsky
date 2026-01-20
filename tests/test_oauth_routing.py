"""Tests for OAuth-first multi-provider fallback routing."""

import pytest
from mcp_bridge.routing.model_tiers import get_oauth_fallback_chain, ModelTier, MODEL_TIERS
from mcp_bridge.routing import get_provider_tracker
from mcp_bridge.orchestrator.router import Router
from mcp_bridge.orchestrator.enums import OrchestrationPhase


def test_oauth_fallback_chain_logic():
    """Verify the fallback chain priorities: Same-tier OAuth -> Lower-tier OAuth -> Same-tier API Key."""
    # Test for Claude 4.5 Opus (Premium)
    provider = "claude"
    model = "claude-4.5-opus"
    chain = get_oauth_fallback_chain(provider, model)

    # 1. Should start with other providers at same tier (OAuth)
    assert chain[0] == ("openai", "gpt-5.2-codex", True)
    assert chain[1] == ("gemini", "gemini-3-pro", True)

    # 2. Then lower tier OAuth
    # (Claude standard, OpenAI standard, Gemini standard - order depends on PROVIDER_FALLBACK_ORDER)
    standard_oauth = [
        c
        for c in chain
        if c[1] in ["claude-4.5-sonnet", "gpt-5.2", "gemini-3-flash-preview"] and c[2] is True
    ]
    assert len(standard_oauth) == 3

    # 3. Then API Key fallbacks (OAuth=False)
    api_key_fallbacks = [c for c in chain if c[2] is False]
    assert len(api_key_fallbacks) == 3
    assert ("claude", "claude-4.5-opus", False) in api_key_fallbacks


def test_router_integration_with_fallback():
    """Test that Router.select_model handles rate limits by traversing the fallback chain."""
    tracker = get_provider_tracker()
    tracker.providers["claude"].reset()
    tracker.providers["openai"].reset()
    tracker.providers["gemini"].reset()

    router = Router()

    # Case 1: Primary provider available
    p = router.select_model(phase=OrchestrationPhase.PLAN, prompt="Fix this bug")
    # By default debugging -> openai
    assert "gpt" in p.lower() or "openai" in p.lower()

    # Case 2: Primary provider rate-limited, should pick first in OAuth chain
    tracker.mark_rate_limited("openai", duration=60)
    p = router.select_model(phase=OrchestrationPhase.PLAN, prompt="Fix this bug")
    # First candidate in chain for OpenAI is Gemini Premium OAuth
    assert "gemini" in p.lower()

    # Case 3: Primary and first fallback rate-limited
    tracker.mark_rate_limited("gemini", duration=60)
    p = router.select_model(phase=OrchestrationPhase.PLAN, prompt="Fix this bug")
    # Second candidate in chain for OpenAI is Claude Premium OAuth
    assert "claude" in p.lower()


def test_model_tier_definitions():
    """Verify models are correctly mapped to tiers."""
    premium_claude = MODEL_TIERS[ModelTier.PREMIUM]["claude"]
    assert premium_claude.model == "claude-4.5-opus"
    assert premium_claude.thinking is True

    standard_gemini = MODEL_TIERS[ModelTier.STANDARD]["gemini"]
    assert standard_gemini.model == "gemini-3-flash-preview"
    assert standard_gemini.thinking is False
