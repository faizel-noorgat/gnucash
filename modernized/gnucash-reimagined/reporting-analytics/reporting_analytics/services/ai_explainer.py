"""AI explainer service — LLM-backed natural-language narratives.

This module takes the *deterministic* output of ``analytics_engine``
(metrics + evidence) and produces a human-readable explanation using
a pluggable LLM provider. The LLM is NEVER asked to perform
arithmetic — it only explains what the metrics mean.

Providers:
  * ``stub``     — returns a canned narrative (used in tests)
  * ``openai``   — calls OpenAI Chat Completions
  * ``anthropic`` — calls Anthropic Messages

The provider is selected via ``LLM_PROVIDER``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings

from ..exceptions import LLMProviderError
from .analytics_engine import AnalyticResult, EvidenceReference

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExplainerResponse:
    """The output of an explanation request."""

    narrative: str
    provider: str
    model: str
    confidence_score: float | None


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


class ExplainerProvider(Protocol):
    def explain(
        self,
        *,
        result: AnalyticResult,
        natural_language_question: str | None,
    ) -> ExplainerResponse: ...


# ---------------------------------------------------------------------------
# Stub provider (for tests and local dev)
# ---------------------------------------------------------------------------


class StubExplainer:
    """Returns a canned narrative based on the metrics.

    The stub is deterministic and does NOT call any external service.
    """

    provider_name = "stub"
    model_name = "stub-v1"

    def explain(
        self,
        *,
        result: AnalyticResult,
        natural_language_question: str | None,
    ) -> ExplainerResponse:
        metric_summary = ", ".join(
            f"{m.name}={m.value}{m.unit}" for m in result.metrics
        )
        narrative = (
            f"Analytic query of kind {result.query_kind.value} produced "
            f"the following metrics: {metric_summary or '(none)'}. "
            f"Evidence references: {len(result.evidence)}."
        )
        return ExplainerResponse(
            narrative=narrative,
            provider=self.provider_name,
            model=self.model_name,
            confidence_score=1.0,
        )


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


class OpenAIExplainer:
    """Calls OpenAI Chat Completions to produce a narrative."""

    provider_name = "openai"

    def __init__(self) -> None:
        self.model = settings.LLM_MODEL or "gpt-4-turbo"
        self.api_key = settings.LLM_API_KEY
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
            with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
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
    """Calls Anthropic Messages to produce a narrative."""

    provider_name = "anthropic"

    def __init__(self) -> None:
        self.model = settings.LLM_MODEL or "claude-3-5-sonnet-20241022"
        self.api_key = settings.LLM_API_KEY
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
            with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
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
    """Return the configured explainer provider."""
    name = settings.LLM_PROVIDER
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

    The caller must have already validated that ``result.evidence`` is
    non-empty (via ``analytics_engine.require_evidence``); if not, we
    raise immediately to prevent hallucinated insights.
    """
    if not result.evidence:
        from ..exceptions import EvidenceMissingError

        raise EvidenceMissingError(
            "refusing to call the LLM with no evidence — an insight must "
            "be backed by concrete ledger references."
        )
    provider = get_provider()
    return provider.explain(
        result=result,
        natural_language_question=natural_language_question,
    )
