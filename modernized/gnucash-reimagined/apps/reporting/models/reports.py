"""Report-related models.

The reporting bounded context distinguishes between:

* ``ReportDefinition`` — a *template* for a standard or custom report
  (balance sheet, income statement, trial balance, or a user-defined
  ad-hoc report). Definitions are reusable and immutable after creation.

* ``ReportParameter`` — a single parameter accepted by a definition
  (date range, account filter, legal-entity filter, …). Parameters are
  validated against a JSON-schema stored on the definition.

* ``ReportInstance`` — a concrete *generated* report. An instance is
  bound to a single tenant, owned by the requesting user, and carries
  its own lifecycle (pending → running → succeeded / failed). An
  instance stores the parameters it was generated with, the SQL query
  that produced it (for reproducibility), the resulting rows, and the
  output artifact (CSV / PDF) if any.

Financial facts are NEVER stored on a ReportInstance — the instance
points at the Accounting Engine's ledger via a frozen query snapshot.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class ReportType(models.TextChoices):
    """Kinds of report the system can produce."""

    BALANCE_SHEET = "balance_sheet", "Balance Sheet"
    INCOME_STATEMENT = "income_statement", "Income Statement"
    CASH_FLOW = "cash_flow", "Cash Flow Statement"
    TRIAL_BALANCE = "trial_balance", "Trial Balance"
    GENERAL_LEDGER = "general_ledger", "General Ledger"
    AGED_RECEIVABLES = "aged_receivables", "Aged Receivables"
    AGED_PAYABLES = "aged_payables", "Aged Payables"
    CUSTOM = "custom", "Custom / Ad-hoc"


class ReportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class OutputFormat(models.TextChoices):
    JSON = "json", "JSON (structured rows)"
    CSV = "csv", "CSV"
    PDF = "pdf", "PDF"
    XLSX = "xlsx", "Excel"


class ReportDefinition(models.Model):
    """Template for a report.

    Standard reports (balance sheet, income statement, …) are seeded at
    migration time. Custom reports are authored by users within a tenant.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="report_definitions",
        db_column="tenant_id",
    )
    code = models.SlugField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=32, choices=ReportType.choices)
    # JSON-Schema describing the parameters this definition accepts.
    parameter_schema = models.JSONField(default=dict, blank=True)
    # The SQL (or Django ORM expression) used to produce rows. Stored so
    # an instance can reproduce the same query later for audit purposes.
    query_template = models.TextField()
    # Default parameter values; merged with per-instance overrides.
    default_parameters = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(
        default=False,
        help_text="System reports cannot be deleted by tenants.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "reporting"
        constraints = [
            # Within a tenant, report codes are unique.
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uq_report_definition_tenant_code"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "report_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class ReportInstance(models.Model):
    """A concrete, generated report.

    The lifecycle is:

        pending → running → succeeded | failed
                  ↓
              cancelled (only from pending/running)

    Financial facts are not stored here. The ``result_rows`` field holds
    the *rendered* output rows; the source of truth remains the
    Accounting Engine's journal.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="report_instances",
        db_column="tenant_id",
    )
    definition = models.ForeignKey(
        ReportDefinition,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_reports",
    )
    status = models.CharField(
        max_length=16, choices=ReportStatus.choices, default=ReportStatus.PENDING
    )
    parameters = models.JSONField(default=dict, blank=True)
    # The SQL that was actually executed (with parameters interpolated),
    # stored for reproducibility / audit.
    executed_query = models.TextField(blank=True)
    # Result payload — the structure depends on OutputFormat:
    #   - JSON: list of dicts
    #   - CSV/PDF/XLSX: object-storage key pointing at the artifact
    result_rows = models.JSONField(default=list, blank=True)
    result_artifact_key = models.CharField(max_length=512, blank=True)
    output_format = models.CharField(
        max_length=8, choices=OutputFormat.choices, default=OutputFormat.JSON
    )
    row_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "reporting"
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.definition.code} #{self.guid} ({self.status})"

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        ReportStatus.PENDING: {ReportStatus.RUNNING, ReportStatus.CANCELLED},
        ReportStatus.RUNNING: {
            ReportStatus.SUCCEEDED,
            ReportStatus.FAILED,
            ReportStatus.CANCELLED,
        },
        ReportStatus.SUCCEEDED: set(),
        ReportStatus.FAILED: set(),
        ReportStatus.CANCELLED: set(),
    }

    def transition_to(self, new_status: str) -> None:
        """Move the instance to ``new_status`` if the transition is legal."""
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"cannot transition ReportInstance from {self.status!r} "
                f"to {new_status!r}"
            )
        self.status = new_status
