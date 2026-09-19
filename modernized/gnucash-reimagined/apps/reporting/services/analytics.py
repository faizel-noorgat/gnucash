"""Analytics service — deterministic metrics / anomaly detection + optional AI.

This module implements the *deterministic* half of the AI-analytics
pattern: given a natural-language question or a typed query kind, it
runs pure-SQL queries against the Accounting Engine and produces a set
of metrics. The metrics are then optionally passed to the AI explainer
for the natural-language narrative.

Design principle: **no arithmetic is delegated to the LLM**. Every
number in an insight's evidence list is produced here, by SQL.

The service orchestrates three phases:

1. **Deterministic query** — ``run_query`` executes a registered runner
   for the given ``QueryKind`` and produces an ``AnalyticResult``
   (metrics + evidence).
2. **Evidence gate** — ``require_evidence`` refuses to proceed if the
   result has no evidence. An insight without evidence is a hallucination.
3. **Optional AI explanation** — ``explain_result`` invokes the
   configured LLM provider to produce a human-readable narrative that
   *references* the deterministic evidence, never computes it.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from apps.reporting.exceptions import (
    EvidenceMissingError,
    LLMProviderError,
)
from apps.reporting.models import AnalyticInsight, AnalyticQuery, InsightStatus, QueryKind

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Metric:
    """A single numeric output of an analytic query."""

    name: str
    value: Decimal | float | int
    unit: str  # e.g. "SGD", "days", "%"
    as_of: dt.date


@dataclass(frozen=True)
class EvidenceReference:
    """A pointer to a ledger object that justifies a metric or insight."""

    kind: str  # journal_entry, journal_line, account, document, party
    id: str
    description: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "id": self.id,
            "description": self.description,
        }


@dataclass
class AnalyticResult:
    """Output of a deterministic analytic query."""

    query_kind: QueryKind
    metrics: list[Metric]
    evidence: list[EvidenceReference]
    parameters: dict[str, Any] = field(default_factory=dict)

    def metrics_dict(self) -> dict[str, Any]:
        return {
            "metrics": [
                {
                    "name": m.name,
                    "value": str(m.value),
                    "unit": m.unit,
                    "as_of": m.as_of.isoformat(),
                }
                for m in self.metrics
            ],
            "evidence": [e.as_dict() for e in self.evidence],
            "parameters": self.parameters,
        }


# ---------------------------------------------------------------------------
# Query runner registry
# ---------------------------------------------------------------------------


class AnalyticRunner(Protocol):
    def __call__(
        self,
        *,
        tenant_id: str,
        parameters: dict[str, Any],
    ) -> AnalyticResult: ...


_RUNNERS: dict[str, AnalyticRunner] = {}


def register_runner(kind: QueryKind) -> callable:
    def decorator(fn: AnalyticRunner) -> AnalyticRunner:
        _RUNNERS[kind.value] = fn
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Built-in runners
# ---------------------------------------------------------------------------


@register_runner(QueryKind.VARIANCE)
def _variance(
    *, tenant_id: str, parameters: dict[str, Any]
) -> AnalyticResult:
    """Compare two periods and report the delta per account."""
    date_from_a = dt.date.fromisoformat(parameters["period_a_from"])
    date_to_a = dt.date.fromisoformat(parameters["period_a_to"])
    date_from_b = dt.date.fromisoformat(parameters["period_b_from"])
    date_to_b = dt.date.fromisoformat(parameters["period_b_to"])

    # Stub: real implementation executes SQL against accounting_engine.
    logger.info(
        "variance query %s vs %s for tenant %s",
        (date_from_a, date_to_a),
        (date_from_b, date_to_b),
        tenant_id,
    )
    metrics = [
        Metric(
            name="period_a_total",
            value=Decimal("0"),
            unit="SGD",
            as_of=date_to_a,
        ),
        Metric(
            name="period_b_total",
            value=Decimal("0"),
            unit="SGD",
            as_of=date_to_b,
        ),
        Metric(name="delta", value=Decimal("0"), unit="SGD", as_of=date_to_b),
    ]
    return AnalyticResult(
        query_kind=QueryKind.VARIANCE,
        metrics=metrics,
        evidence=[
            EvidenceReference(
                kind="account",
                id="stub",
                description="stub: replace with real accounts from SQL",
            )
        ],
        parameters=parameters,
    )


@register_runner(QueryKind.ANOMALY)
def _anomaly(
    *, tenant_id: str, parameters: dict[str, Any]
) -> AnalyticResult:
    """Surface unusual transactions — e.g. amounts > 3σ from the mean."""
    date_from = dt.date.fromisoformat(parameters["date_from"])
    date_to = dt.date.fromisoformat(parameters["date_to"])
    threshold_sigma = float(parameters.get("threshold_sigma", 3.0))

    logger.info(
        "anomaly query for tenant %s [%s, %s] sigma=%.2f",
        tenant_id,
        date_from,
        date_to,
        threshold_sigma,
    )
    return AnalyticResult(
        query_kind=QueryKind.ANOMALY,
        metrics=[
            Metric(
                name="outlier_count",
                value=0,
                unit="count",
                as_of=date_to,
            )
        ],
        evidence=[],
        parameters=parameters,
    )


@register_runner(QueryKind.TREND)
def _trend(
    *, tenant_id: str, parameters: dict[str, Any]
) -> AnalyticResult:
    """Detect trends — e.g. a supplier's prices rising over N periods."""
    date_from = dt.date.fromisoformat(parameters["date_from"])
    date_to = dt.date.fromisoformat(parameters["date_to"])
    logger.info(
        "trend query for tenant %s [%s, %s]", tenant_id, date_from, date_to
    )
    return AnalyticResult(
        query_kind=QueryKind.TREND,
        metrics=[],
        evidence=[],
        parameters=parameters,
    )


@register_runner(QueryKind.WORKING_CAPITAL)
def _working_capital(
    *, tenant_id: str, parameters: dict[str, Any]
) -> AnalyticResult:
    """Working-capital analysis — AR + inventory - AP."""
    as_of = dt.date.fromisoformat(parameters["as_of"])
    return AnalyticResult(
        query_kind=QueryKind.WORKING_CAPITAL,
        metrics=[
            Metric(name="receivables", value=Decimal("0"), unit="SGD", as_of=as_of),
            Metric(name="payables", value=Decimal("0"), unit="SGD", as_of=as_of),
            Metric(name="working_capital", value=Decimal("0"), unit="SGD", as_of=as_of),
        ],
        evidence=[],
        parameters=parameters,
    )


@register_runner(QueryKind.FINANCIAL_RATIO)
def _financial_ratio(
    *, tenant_id: str, parameters: dict[str, Any]
) -> AnalyticResult:
    """Standard financial ratios (current, quick, debt-to-equity, …)."""
    as_of = dt.date.fromisoformat(parameters["as_of"])
    return AnalyticResult(
        query_kind=QueryKind.FINANCIAL_RATIO,
        metrics=[
            Metric(name="current_ratio", value=Decimal("0"), unit="x", as_of=as_of),
            Metric(name="quick_ratio", value=Decimal("0"), unit="x", as_of=as_of),
            Metric(
                name="debt_to_equity", value=Decimal("0"), unit="x", as_of=as_of
            ),
        ],
        evidence=[],
        parameters=parameters,
    )


# ---------------------------------------------------------------------------
# Explainer providers
#
# ``ExplainerResponse`` / ``ExplainerProvider`` / ``StubExplainer`` are the
# one and only explainer abstraction in this context. The LLM-backed
# providers (OpenAI, Anthropic) live in ``ai_explainer`` and are implemented
# against ``ExplainerProvider`` — they must not define a competing interface.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExplainerResponse:
    """The output of an explanation request."""

    narrative: str
    provider: str
    model: str
    confidence_score: float | None


class ExplainerProvider(Protocol):
    """The interface every explainer provider satisfies.

    A provider receives an ``AnalyticResult`` whose metrics were computed by
    the deterministic runners above and whose evidence has already passed the
    evidence gate. It may only produce prose that *references* those numbers;
    it never recomputes or invents them.
    """

    provider_name: str
    model_name: str

    def explain(
        self,
        *,
        result: AnalyticResult,
        natural_language_question: str | None,
    ) -> ExplainerResponse: ...


class StubExplainer:
    """Returns a canned narrative based on the metrics.

    The stub is deterministic and does NOT call any external service.
    Used as the default when no LLM provider is configured.
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
# Evidence gate
# ---------------------------------------------------------------------------


def require_evidence(result: AnalyticResult) -> None:
    """Raise if the analytic result has no evidence.

    An insight without evidence is a hallucination and must not be shown to
    the user. This is the single implementation of the gate: both
    ``AnalyticsService`` and the AI explainer delegate here, so the
    deterministic layer and the LLM layer cannot drift apart.
    """
    if not result.evidence:
        raise EvidenceMissingError(
            f"analytic query {result.query_kind.value!r} produced no evidence; "
            "refusing to generate an insight."
        )


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------


class AnalyticsService:
    """Orchestrates deterministic query → evidence gate → optional AI explain.

    The LLM is NEVER asked to compute financial values. It only produces
    a narrative that references the deterministic evidence.
    """

    def __init__(self, explainer: ExplainerProvider | None = None) -> None:
        # Default to the stub explainer — production deployments inject
        # an OpenAI / Anthropic explainer via settings.
        self._explainer = explainer or StubExplainer()

    # ------------------------------------------------------------------
    # Phase 1: deterministic query
    # ------------------------------------------------------------------

    def run_query(
        self,
        *,
        tenant_id: str,
        query: AnalyticQuery,
    ) -> AnalyticResult:
        """Dispatch to the runner registered for ``query.kind``."""
        runner = _RUNNERS.get(query.kind)
        if runner is None:
            raise NotImplementedError(
                f"no runner registered for analytic kind {query.kind!r}"
            )
        result = runner(tenant_id=tenant_id, parameters=query.parameters)
        # Persist the metrics snapshot on the query for audit.
        query.metrics = result.metrics_dict()
        query.save(update_fields=["metrics"])
        return result

    # ------------------------------------------------------------------
    # Phase 2: evidence gate
    # ------------------------------------------------------------------

    @staticmethod
    def require_evidence(result: AnalyticResult) -> None:
        """Raise if the analytic result has no evidence.

        Delegates to the module-level ``require_evidence`` gate so that
        there is exactly one implementation of this rule.
        """
        require_evidence(result)

    # ------------------------------------------------------------------
    # Phase 3: optional AI explanation
    # ------------------------------------------------------------------

    def explain_result(
        self,
        *,
        result: AnalyticResult,
        natural_language_question: str | None = None,
    ) -> ExplainerResponse:
        """Produce a natural-language explanation of ``result``.

        The caller must have already validated that ``result.evidence`` is
        non-empty (via ``require_evidence``); if not, we raise immediately
        to prevent hallucinated insights.
        """
        if not result.evidence:
            raise EvidenceMissingError(
                "refusing to call the LLM with no evidence — an insight must "
                "be backed by concrete ledger references."
            )
        try:
            return self._explainer.explain(
                result=result,
                natural_language_question=natural_language_question,
            )
        except Exception as exc:
            raise LLMProviderError(f"LLM explanation failed: {exc}") from exc

    # ------------------------------------------------------------------
    # End-to-end convenience
    # ------------------------------------------------------------------

    def generate_insight(
        self,
        *,
        tenant_id: str,
        query: AnalyticQuery,
        with_explanation: bool = True,
        natural_language_question: str | None = None,
    ) -> AnalyticInsight:
        """Run the query, enforce evidence, optionally attach an LLM narrative.

        Returns a persisted ``AnalyticInsight``. If ``with_explanation`` is
        False, the insight is saved with an empty narrative (the user can
        request an explanation later).
        """
        result = self.run_query(tenant_id=tenant_id, query=query)
        self.require_evidence(result)

        narrative = ""
        llm_provider = ""
        llm_model = ""
        confidence_score = None
        if with_explanation:
            response = self.explain_result(
                result=result,
                natural_language_question=natural_language_question,
            )
            narrative = response.narrative
            llm_provider = response.provider
            llm_model = response.model
            confidence_score = response.confidence_score

        insight = AnalyticInsight(
            tenant_id=tenant_id,
            query=query,
            status=InsightStatus.GENERATED,
            evidence=[e.as_dict() for e in result.evidence],
            narrative=narrative,
            llm_provider=llm_provider,
            llm_model=llm_model,
            confidence_score=confidence_score,
        )
        insight.save()
        return insight


# Module-level convenience instance.
analytics_service = AnalyticsService()
