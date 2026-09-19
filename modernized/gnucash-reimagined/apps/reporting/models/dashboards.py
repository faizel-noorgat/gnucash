"""Dashboard and KPI models.

A ``Dashboard`` is a named, tenant-scoped container of widgets. Each
``DashboardWidget`` renders a single metric or chart using either:

* a standard report definition (the widget re-runs the report with
  fixed parameters), or
* a pre-built KPI function registered in
  ``apps.reporting.services.kpis``.

Widget output is cached in Redis for a short TTL; the underlying
financial facts still come from the Accounting Engine.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class WidgetType(models.TextChoices):
    REPORT = "report", "Standard report"
    KPI = "kpi", "Pre-built KPI"
    CHART = "chart", "Chart (line, bar, pie, …)"
    TEXT = "text", "Static text / markdown"


class Dashboard(models.Model):
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="dashboards",
        db_column="tenant_id",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_dashboards",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(
        default=False,
        help_text="A tenant may have at most one default dashboard.",
    )
    layout = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of widget placements (grid coordinates).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "reporting"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(is_default=True),
                name="uq_dashboard_tenant_default",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class DashboardWidget(models.Model):
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(
        Dashboard, on_delete=models.CASCADE, related_name="widgets"
    )
    widget_type = models.CharField(max_length=16, choices=WidgetType.choices)
    title = models.CharField(max_length=255)
    # Either a FK to a report definition OR a dotted path to a KPI
    # function, depending on widget_type.
    report_definition = models.ForeignKey(
        "reporting.ReportDefinition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="widgets",
    )
    kpi_name = models.CharField(max_length=128, blank=True)
    # Parameters passed through to the report / KPI.
    parameters = models.JSONField(default=dict, blank=True)
    # Visual config — chart type, colors, thresholds, etc.
    visual_config = models.JSONField(default=dict, blank=True)
    position = models.IntegerField(default=0)
    cache_ttl_seconds = models.IntegerField(default=300)

    class Meta:
        app_label = "reporting"
        ordering = ["position"]

    def __str__(self) -> str:
        return f"{self.title} ({self.widget_type})"
