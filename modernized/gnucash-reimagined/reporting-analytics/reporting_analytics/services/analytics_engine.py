"""Analytics engine — deterministic metrics / anomaly detection.

This module implements the *deterministic* half of the AI-analytics
pattern: given a natural-language question or a typed query kind, it
runs pure-SQL queries against the Accounting Engine and produces a set
of metrics. The metrics are then passed to ``ai_explainer`` for the
natural-language narrative.

Design principle: **no arithmetic is delegated to the LLM**. Every
number in an insight's evidence list is produced here, by SQL.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from ..exceptions import EvidenceMissingError
from ..models import AnalyticQuery, QueryKind

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
# Query runner
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


def run_analytic_query(
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
    return runner(tenant_id=tenant_id, parameters=query.parameters)


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

    # The actual SQL would join the Accounting Engine's journal_line and
    # group by account. For scaffolding purposes we return the *shape*
    # of the result; the SQL is left as a clearly-marked stub.
    logger.info(
        "variance query %s vs %s for tenant %s",
        (date_from_a, date_to_a),
        (date_from_b, date_to_b),
        tenant_id,
    )

    # Placeholder metrics — the real implementation would execute SQL.
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

    # Stub — real implementation computes mean/stddev over the period and
    # flags outliers.
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


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def require_evidence(result: AnalyticResult) -> None:
    """Raise if the analytic result has no evidence.

    Called by the insight-persistence layer. An insight without evidence
    is a hallucination and must not be shown to the user.
    """
    if not result.evidence:
        raise EvidenceMissingError(
            f"analytic query {result.query_kind.value!r} produced no evidence; "
            "refusing to generate an insight."
        )
