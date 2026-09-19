"""Analytics models — AI-assisted insights and their evidence.

Design principles (Section 9.7 of the spec):

1. **Deterministic query first.** Every ``AnalyticQuery`` executes a
   pure-SQL (or ORM) query against the Accounting Engine to produce a
   set of metrics or anomalies.
2. **Evidence is mandatory.** Each ``AnalyticInsight`` references the
   concrete ledger rows, journal entries, and accounts that justify
   the insight. If evidence is missing, the insight is not persisted.
3. **LLM is for explanation only.** The natural-language narrative is
   produced by a pluggable LLM provider; arithmetic is never delegated.

The ``status`` field records whether the insight has been generated,
reviewed by a human, or rejected.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class QueryKind(models.TextChoices):
    VARIANCE = "variance", "Variance analysis"
    TREND = "trend", "Trend detection"
    ANOMALY = "anomaly", "Anomaly surfacing"
    WORKING_CAPITAL = "working_capital", "Working-capital analysis"
    CASH_FLOW_FORECAST = "cash_flow_forecast", "Cash-flow forecast"
    FINANCIAL_RATIO = "financial_ratio", "Financial ratio"
    CUSTOM = "custom", "Custom analytic query"


class InsightStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    GENERATED = "generated", "Generated"
    REVIEWED = "reviewed", "Reviewed"
    REJECTED = "rejected", "Rejected"


class AnalyticQuery(models.Model):
    """A deterministic query that produces metrics / anomalies.

    The query itself is stored as a frozen SQL string plus the
    parameters it was invoked with, so the result is reproducible.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="analytic_queries",
        db_column="tenant_id",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytic_queries",
    )
    kind = models.CharField(max_length=32, choices=QueryKind.choices)
    natural_language_question = models.TextField(
        blank=True,
        help_text="Free-form question from the user, if any.",
    )
    # The frozen SQL / ORM expression that was executed.
    executed_query = models.TextField(blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    # Raw metrics output (JSON). The shape depends on ``kind``.
    metrics = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "reporting"
        indexes = [
            models.Index(fields=["tenant", "kind"]),
            models.Index(fields=["tenant", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind} #{self.guid}"


class AnalyticInsight(models.Model):
    """An AI-generated insight, always backed by concrete evidence.

    The ``evidence`` field stores a list of references to ledger rows —
    journal entries, accounts, documents — that justify the narrative.
    The ``narrative`` field is the LLM-produced explanation.

    If ``evidence`` is empty, the insight must NOT be persisted — the
    ``save()`` method enforces this.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="analytic_insights",
        db_column="tenant_id",
    )
    query = models.ForeignKey(
        AnalyticQuery,
        on_delete=models.CASCADE,
        related_name="insights",
    )
    status = models.CharField(
        max_length=16,
        choices=InsightStatus.choices,
        default=InsightStatus.PENDING,
    )
    # The evidence: list of dicts with {kind, id, description}.
    # kind is one of: journal_entry, journal_line, account, document, party.
    evidence = models.JSONField(default=list)
    # The LLM-produced narrative.
    narrative = models.TextField(blank=True)
    # Which LLM provider / model produced the narrative.
    llm_provider = models.CharField(max_length=64, blank=True)
    llm_model = models.CharField(max_length=128, blank=True)
    # Confidence score from the LLM, if available.
    confidence_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_insights",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "reporting"
        indexes = [
            models.Index(fields=["tenant", "status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Insight #{self.guid} ({self.status})"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.evidence:
            # Evidence is mandatory — an insight without evidence is a
            # hallucination and must not be persisted.
            raise ValueError(
                "AnalyticInsight must have at least one evidence reference; "
                "refusing to persist a hallucinated insight."
            )
        super().save(*args, **kwargs)
