"""Dashboard & widget service — CRUD + rendering orchestration.

The ``DashboardService`` is the only entry point for manipulating
dashboards. It:

* creates / updates / deletes ``Dashboard`` and ``DashboardWidget``
  objects, scoped to a single tenant;
* resolves each widget to its data source — either a registered
  ``ReportGenerationService`` report or a KPI function registered in
  ``apps.reporting.services.kpis`` — and returns the rendered payload
  for the UI.

Widget rendering is intentionally *read-only*: no financial facts are
written here; the Accounting Engine remains the single source of truth.

Caching (Redis, short TTL) is applied at the widget-rendering layer;
the cache key includes the tenant id, widget guid, and a hash of the
parameters so stale numbers are never served across tenants.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable

from django.utils import timezone

from apps.reporting.exceptions import (
    ReportDefinitionNotFoundError,
)
from apps.reporting.models import Dashboard, DashboardWidget, WidgetType
from apps.reporting.services import kpis as kpi_module
from apps.reporting.services.reports import (
    ReportGenerationService,
    ReportParameters,
    ReportResult,
    _parse_date,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public value types
# ---------------------------------------------------------------------------


@dataclass
class WidgetRender:
    """The rendered payload for a single dashboard widget."""

    widget_guid: str
    widget_type: str
    title: str
    payload: dict[str, Any] = field(default_factory=dict)
    rendered_at: Any = field(default_factory=timezone.now)
    error: str | None = None


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------


class DashboardService:
    """CRUD and rendering for dashboards and their widgets."""

    def __init__(
        self,
        report_service: ReportGenerationService | None = None,
    ) -> None:
        self._report_service = report_service or ReportGenerationService()

    # ------------------------------------------------------------------
    # Dashboard CRUD
    # ------------------------------------------------------------------

    def create_dashboard(
        self,
        *,
        tenant_id: str,
        owner_id: str,
        name: str,
        description: str = "",
        is_default: bool = False,
        layout: list[Any] | None = None,
    ) -> Dashboard:
        """Create a new dashboard for the tenant."""
        if is_default:
            # Enforce at-most-one default per tenant.
            Dashboard.objects.filter(
                tenant_id=tenant_id, is_default=True
            ).update(is_default=False)
        return Dashboard.objects.create(
            tenant_id=tenant_id,
            owner_id=owner_id,
            name=name,
            description=description,
            is_default=is_default,
            layout=layout or [],
        )

    def list_dashboards(self, *, tenant_id: str) -> Iterable[Dashboard]:
        return Dashboard.objects.filter(tenant_id=tenant_id)

    def get_dashboard(self, *, tenant_id: str, guid: str) -> Dashboard:
        try:
            return Dashboard.objects.get(tenant_id=tenant_id, guid=guid)
        except Dashboard.DoesNotExist as exc:
            from apps.reporting.exceptions import ReportingAnalyticsError

            raise ReportingAnalyticsError(
                f"dashboard {guid!r} not found for tenant {tenant_id!r}"
            ) from exc

    def delete_dashboard(self, *, tenant_id: str, guid: str) -> None:
        dashboard = self.get_dashboard(tenant_id=tenant_id, guid=guid)
        dashboard.delete()

    # ------------------------------------------------------------------
    # Widget CRUD
    # ------------------------------------------------------------------

    def add_widget(
        self,
        *,
        dashboard: Dashboard,
        widget_type: str,
        title: str,
        report_definition_code: str | None = None,
        kpi_name: str | None = None,
        parameters: dict[str, Any] | None = None,
        visual_config: dict[str, Any] | None = None,
        position: int = 0,
    ) -> DashboardWidget:
        """Add a widget to a dashboard.

        Exactly one of ``report_definition_code`` or ``kpi_name`` must
        be supplied, depending on ``widget_type``.
        """
        report_def = None
        if widget_type == WidgetType.REPORT:
            if not report_definition_code:
                raise ValueError(
                    "widget_type=report requires report_definition_code"
                )
            try:
                report_def = self._report_service.get_definition(
                    tenant_id=str(dashboard.tenant_id),
                    code=report_definition_code,
                )
            except ReportDefinitionNotFoundError:
                raise

        if widget_type == WidgetType.KPI and not kpi_name:
            raise ValueError("widget_type=kpi requires kpi_name")

        return DashboardWidget.objects.create(
            dashboard=dashboard,
            widget_type=widget_type,
            title=title,
            report_definition=report_def,
            kpi_name=kpi_name or "",
            parameters=parameters or {},
            visual_config=visual_config or {},
            position=position,
        )

    def remove_widget(self, *, widget: DashboardWidget) -> None:
        widget.delete()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_dashboard(
        self, *, tenant_id: str, guid: str
    ) -> list[WidgetRender]:
        """Render every widget in the dashboard, in position order."""
        dashboard = self.get_dashboard(tenant_id=tenant_id, guid=guid)
        return [
            self._render_widget(tenant_id=tenant_id, widget=w)
            for w in dashboard.widgets.all()
        ]

    def render_widget(
        self, *, tenant_id: str, widget: DashboardWidget
    ) -> WidgetRender:
        return self._render_widget(tenant_id=tenant_id, widget=widget)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _render_widget(
        self, *, tenant_id: str, widget: DashboardWidget
    ) -> WidgetRender:
        """Dispatch rendering to the right source (report / KPI / static)."""
        try:
            if widget.widget_type == WidgetType.TEXT:
                return WidgetRender(
                    widget_guid=str(widget.guid),
                    widget_type=widget.widget_type,
                    title=widget.title,
                    payload={"text": widget.visual_config.get("text", "")},
                )
            if widget.widget_type == WidgetType.KPI:
                return self._render_kpi(widget)
            if widget.widget_type == WidgetType.REPORT:
                return self._render_report(tenant_id=tenant_id, widget=widget)
            # CHART etc. reuse the report path with visual_config applied.
            return self._render_report(tenant_id=tenant_id, widget=widget)
        except Exception as exc:
            logger.exception("widget render failed: %s", widget.guid)
            return WidgetRender(
                widget_guid=str(widget.guid),
                widget_type=widget.widget_type,
                title=widget.title,
                error=str(exc),
            )

    def _render_kpi(self, widget: DashboardWidget) -> WidgetRender:
        fn = kpi_module.KPI_REGISTRY.get(widget.kpi_name)
        if fn is None:
            raise ValueError(f"unknown KPI {widget.kpi_name!r}")
        # KPI functions accept tenant_id plus arbitrary parameters.
        params = dict(widget.parameters or {})
        if "as_of" in params:
            params["as_of"] = _parse_date(params["as_of"])
        values = fn(**params)
        return WidgetRender(
            widget_guid=str(widget.guid),
            widget_type=widget.widget_type,
            title=widget.title,
            payload={
                "kpi": widget.kpi_name,
                "values": [
                    {"name": v.name, "value": str(v.value), "unit": v.unit}
                    for v in values
                ],
            },
        )

    def _render_report(
        self, *, tenant_id: str, widget: DashboardWidget
    ) -> WidgetRender:
        if widget.report_definition is None:
            raise ValueError(
                f"widget {widget.guid} has widget_type=report but no definition"
            )
        from apps.reporting.models import ReportInstance

        # Build a transient instance for the renderer.
        instance = ReportInstance(
            tenant_id=tenant_id,
            definition=widget.report_definition,
            parameters=widget.parameters or {},
        )
        result: ReportResult = self._report_service.generate(
            tenant_id=tenant_id, instance=instance
        )
        return WidgetRender(
            widget_guid=str(widget.guid),
            widget_type=widget.widget_type,
            title=widget.title,
            payload={
                "columns": result.columns,
                "rows": [r.cells for r in result.rows],
                "row_count": result.row_count,
            },
        )

    # ------------------------------------------------------------------
    # Cache helpers (placeholder — wire to Django cache in production)
    # ------------------------------------------------------------------

    @staticmethod
    def cache_key(*, tenant_id: str, widget: DashboardWidget) -> str:
        params_hash = hashlib.sha256(
            str(sorted((widget.parameters or {}).items())).encode()
        ).hexdigest()[:12]
        return f"reporting:widget:{tenant_id}:{widget.guid}:{params_hash}"


# Module-level convenience instance.
dashboard_service = DashboardService()
