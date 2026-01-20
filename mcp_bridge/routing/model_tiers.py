"""Model tier definitions and cross-provider fallback planning.

This module centralizes a simple, two-tier model architecture and provides
a deterministic fallback chain when an OAuth call fails or is unavailable.

The fallback chain is ordered to prefer:
1) Same-tier OAuth models on *other* providers
2) Lower-tier OAuth models (if available)
3) Same-tier models via API key auth

The boolean in the returned tuples indicates whether OAuth should be used.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


class ModelTier(str, Enum):
    PREMIUM = "premium"
    STANDARD = "standard"


@dataclass(frozen=True)
class TierModel:
    model: str
    thinking: bool


KNOWN_PROVIDERS: Final[tuple[str, ...]] = ("claude", "openai", "gemini")

# Provider preference order mirrors existing routing fallback chains.
PROVIDER_FALLBACK_ORDER: Final[dict[str, list[str]]] = {
    "claude": ["openai", "gemini"],
    "openai": ["gemini", "claude"],
    "gemini": ["openai", "claude"],
}

# Ordered best -> worst.
TIER_ORDER: Final[tuple[ModelTier, ...]] = (ModelTier.PREMIUM, ModelTier.STANDARD)

MODEL_TIERS: Final[dict[ModelTier, dict[str, TierModel]]] = {
    ModelTier.PREMIUM: {
        "claude": TierModel(model="claude-4.5-opus", thinking=True),
        "openai": TierModel(model="gpt-5.2-codex", thinking=False),
        "gemini": TierModel(model="gemini-3-pro", thinking=False),
    },
    ModelTier.STANDARD: {
        "claude": TierModel(model="claude-4.5-sonnet", thinking=False),
        "openai": TierModel(model="gpt-5.2", thinking=False),
        "gemini": TierModel(model="gemini-3-flash-preview", thinking=False),
    },
}


def _require_known_provider(provider: str) -> None:
    if provider not in KNOWN_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider!r}. Expected one of {KNOWN_PROVIDERS!r}.")


def _tier_for(provider: str, model: str) -> ModelTier:
    _require_known_provider(provider)

    for tier, tier_models in MODEL_TIERS.items():
        spec = tier_models.get(provider)
        if spec and spec.model == model:
            return tier

    raise ValueError(
        f"Unknown model for provider {provider!r}: {model!r}. "
        "Expected a model present in MODEL_TIERS."
    )


def _providers_other_first(provider: str) -> list[str]:
    _require_known_provider(provider)
    preferred = PROVIDER_FALLBACK_ORDER.get(provider)
    if preferred is not None:
        return [p for p in preferred if p != provider]
    return [p for p in KNOWN_PROVIDERS if p != provider]


def _lower_tiers(tier: ModelTier) -> list[ModelTier]:
    try:
        idx = TIER_ORDER.index(tier)
    except ValueError:
        return []
    return list(TIER_ORDER[idx + 1 :])


def get_oauth_fallback_chain(provider: str, model: str) -> list[tuple[str, str, bool]]:
    """Return ordered (provider, model, use_oauth) fallbacks.

    Args:
        provider: Current provider (e.g. "openai")
        model: Current model identifier within that provider

    Returns:
        A list of candidate (provider, model, use_oauth) tuples.

    Ordering rules:
        - Same-tier models on OTHER providers first (OAuth)
        - Then lower-tier models (OAuth)
        - Then same-tier models via API key (non-OAuth)
    """

    tier = _tier_for(provider, model)
    other_providers = _providers_other_first(provider)

    chain: list[tuple[str, str, bool]] = []
    seen: set[tuple[str, str, bool]] = set()

    def add(p: str, m: str, use_oauth: bool) -> None:
        item = (p, m, use_oauth)
        if item in seen:
            return
        seen.add(item)
        chain.append(item)

    # 1) Same tier, other providers, OAuth first.
    for p in other_providers:
        add(p, MODEL_TIERS[tier][p].model, True)

    # 2) Lower tiers, OAuth.
    for lower in _lower_tiers(tier):
        for p in [*other_providers, provider]:
            add(p, MODEL_TIERS[lower][p].model, True)

    # 3) Same tier, API key (non-OAuth).
    for p in [provider, *other_providers]:
        add(p, MODEL_TIERS[tier][p].model, False)

    return chain
