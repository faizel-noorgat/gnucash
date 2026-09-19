"""AI explainer service — LLM-backed natural-language narratives.

This module implements the *optional* last phase of the AI-analytics
pattern: **deterministic query → computed evidence → optional AI
explanation**.

Every number a provider in this module ever sees was produced by the SQL
runners in ``apps.reporting.services.analytics``. The LLM is NEVER asked to
perform arithmetic; it only explains what the already-computed metrics mean.
That rule is enforced structurally — the prompt built below renders metric
values that were computed elsewhere, and the evidence gate refuses to call a
provider at all when the deterministic layer produced no evidence.

Providers:
  * ``stub``      — returns a canned narrative (used in tests and local dev)
  * ``openai``    — calls OpenAI Chat Completions
  * ``anthropic`` — calls Anthropic Messages

The provider is selected via ``settings.LLM_PROVIDER``, defaulting to
``stub`` when the unified settings do not define it.

``StubExplainer``, ``ExplainerResponse``, the ``ExplainerProvider``
protocol and the ``require_evidence`` gate are all defined once, in
``analytics``, and re-exported here: this module adds providers, not a
second explainer abstraction.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from apps.reporting.exceptions import LLMProviderError

from .analytics import (
    AnalyticResult,
    EvidenceReference,
    ExplainerProvider,
    ExplainerResponse,
    StubExplainer,
    require_evidence,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings lookups
#
# The standalone service read LLM_MODEL / LLM_API_KEY / LLM_TIMEOUT_SECONDS /
# LLM_PROVIDER straight off ``django.conf.settings``. The unified settings
# module does not define them, so each is read with a conservative default:
# an unconfigured deployment silently stays on the deterministic stub rather
# than failing at import time.
# ---------------------------------------------------------------------------

DEFAULT_PROVIDER = "stub"
DEFAULT_OPENAI_MODEL = "gpt-4-turbo"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
DEFAULT_TIMEOUT_SECONDS = 30.0


def _llm_setting(name: str, default: Any) -> Any:
    """Read an LLM setting, falling back to ``default`` when unset."""
    return getattr(settings, name, default)


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


class OpenAIExplainer:
    """Calls OpenAI Chat Completions to produce a narrative.

    The provider is deliberately arithmetic-free: it is handed metrics that
    were already computed by the deterministic layer and asked only to
    explain their meaning.
    """

    provider_name = "openai"

    def __init__(self) -> None:
        self.model = _llm_setting("LLM_MODEL", None) or DEFAULT_OPENAI_MODEL
        self.api_key = _llm_setting("LLM_API_KEY", None)
        if not self.api_key:
            raise LLMProviderError(
                "LLM_API_KEY is not configured for OpenAI provider."
            )

    def explain(
        self,
        *,
        result: AnalyticResult,
        natural_language_question: str | None,
    ) -> ExplainerResponse:
        import httpx

        prompt = self._build_prompt(result, natural_language_question)
        try:
            timeout = _llm_setting("LLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are an accounting analyst. Explain the "
                                    "following metrics to a non-technical user. "
                                    "Do NOT perform arithmetic; only explain what "
                                    "the numbers mean."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                data = response.json()
                narrative = data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise LLMProviderError(f"OpenAI call failed: {exc}") from exc

        return ExplainerResponse(
            narrative=narrative,
            provider=self.provider_name,
            model=self.model,
            confidence_score=None,
        )

    def _build_prompt(
        self, result: AnalyticResult, question: str | None
    ) -> str:
        lines = [f"Query kind: {result.query_kind.value}"]
        if question:
            lines.append(f"User question: {question}")
        lines.append("Metrics:")
        for m in result.metrics:
            lines.append(f"  - {m.name}: {m.value} {m.unit} (as of {m.as_of})")
        lines.append("Evidence:")
        for e in result.evidence:
            lines.append(f"  - {e.kind} {e.id}: {e.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------


class AnthropicExplainer:
    """Calls Anthropic Messages to produce a narrative.

    As with the OpenAI provider, the model narrates pre-computed metrics and
    is never used as a calculator.
    """

    provider_name = "anthropic"

    def __init__(self) -> None:
        self.model = _llm_setting("LLM_MODEL", None) or DEFAULT_ANTHROPIC_MODEL
        self.api_key = _llm_setting("LLM_API_KEY", None)
        if not self.api_key:
            raise LLMProviderError(
                "LLM_API_KEY is not configured for Anthropic provider."
            )

    def explain(
        self,
        *,
        result: AnalyticResult,
        natural_language_question: str | None,
    ) -> ExplainerResponse:
        import httpx

        prompt = self._build_prompt(result, natural_language_question)
        try:
            timeout = _llm_setting("LLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 1024,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt,
                            }
                        ],
                    },
                )
                response.raise_for_status()
                data = response.json()
                narrative = data["content"][0]["text"]
        except Exception as exc:
            raise LLMProviderError(f"Anthropic call failed: {exc}") from exc

        return ExplainerResponse(
            narrative=narrative,
            provider=self.provider_name,
            model=self.model,
            confidence_score=None,
        )

    def _build_prompt(
        self, result: AnalyticResult, question: str | None
    ) -> str:
        lines = [f"Query kind: {result.query_kind.value}"]
        if question:
            lines.append(f"User question: {question}")
        lines.append("Metrics:")
        for m in result.metrics:
            lines.append(f"  - {m.name}: {m.value} {m.unit} (as of {m.as_of})")
        lines.append("Evidence:")
        for e in result.evidence:
            lines.append(f"  - {e.kind} {e.id}: {e.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


_PROVIDERS: dict[str, type[StubExplainer | OpenAIExplainer | AnthropicExplainer]] = {
    "stub": StubExplainer,
    "openai": OpenAIExplainer,
    "anthropic": AnthropicExplainer,
}


def get_provider() -> ExplainerProvider:
    """Return the configured explainer provider.

    Defaults to the deterministic stub when ``LLM_PROVIDER`` is unset, so an
    unconfigured deployment keeps working without ever reaching an LLM.
    """
    name = _llm_setting("LLM_PROVIDER", DEFAULT_PROVIDER)
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise LLMProviderError(
            f"unknown LLM_PROVIDER {name!r}; expected one of {sorted(_PROVIDERS)}"
        )
    return cls()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def explain(
    *,
    result: AnalyticResult,
    natural_language_question: str | None = None,
) -> ExplainerResponse:
    """Produce a natural-language explanation of ``result``.

    The evidence gate runs first: an insight with no evidence is a
    hallucination, so the provider is never called at all. This is the same
    gate ``AnalyticsService`` uses — there is only one.
    """
    require_evidence(result)
    provider = get_provider()
    return provider.explain(
        result=result,
        natural_language_question=natural_language_question,
    )


__all__ = [
    "AnthropicExplainer",
    "EvidenceReference",
    "ExplainerProvider",
    "ExplainerResponse",
    "OpenAIExplainer",
    "StubExplainer",
    "explain",
    "get_provider",
    "require_evidence",
]
