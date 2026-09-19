"""API views for the Reporting & Analytics bounded context.

The views are thin DRF viewsets that delegate to the domain services:

* ``ReportGenerationService`` — deterministic report generation.
* ``AnalyticsService`` — deterministic queries + optional AI explanation.
* ``DashboardService`` — dashboard / widget CRUD.

All views are tenant-scoped. The ``tenant_id`` is taken from the
authenticated user's active tenant (set by middleware); cross-tenant
access is rejected at the service layer.
"""

from __future__ import annotations

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.reporting.exceptions import (
    ReportDefinitionNotFoundError,
    ReportParametersInvalidError,
)

logger = logging.getLogger(__name__)


class _TenantScopedMixin:
    """Mixin that extracts the active tenant from the request.

    The real implementation reads ``request.tenant`` (set by the
    tenant-context middleware). For scaffolding purposes we fall back
    to a query-parameter so the view can be exercised without auth.
    """

    def _tenant_id(self, request: Request) -> str:
        tenant = getattr(request, "tenant", None)
        if tenant is not None:
            return str(tenant.guid)
        fallback = request.query_params.get("tenant_id") or request.data.get(
            "tenant_id"
        )
        if not fallback:
            from apps.reporting.exceptions import TenantRequiredError

            raise TenantRequiredError(
                "no tenant context on request; supply tenant_id"
            )
        return str(fallback)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class ReportDefinitionViewSet(_TenantScopedMixin, viewsets.ViewSet):
    """List / retrieve standard and custom report definitions."""

    def list(self, request: Request) -> Response:  # noqa: A003
        from apps.reporting.services.reports import report_service

        tenant_id = self._tenant_id(request)
        definitions = report_service.list_definitions(tenant_id=tenant_id)
        payload = [
            {
                "guid": str(d.guid),
                "code": d.code,
                "name": d.name,
                "report_type": d.report_type,
                "is_system": d.is_system,
            }
            for d in definitions
        ]
        return Response(payload)

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        from apps.reporting.services.reports import report_service

        tenant_id = self._tenant_id(request)
        try:
            definition = report_service.get_definition(
                tenant_id=tenant_id, code=pk
            )
        except ReportDefinitionNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "guid": str(definition.guid),
                "code": definition.code,
                "name": definition.name,
                "report_type": definition.report_type,
                "is_system": definition.is_system,
            }
        )


class ReportInstanceViewSet(_TenantScopedMixin, viewsets.ViewSet):
    """Create / inspect generated reports.

    POST body: ``{definition_code, parameters, output_format?}``.
    The actual generation is synchronous in v1; a future revision will
    dispatch to Celery and return the pending instance.
    """

    def list(self, request: Request) -> Response:  # noqa: A003
        # Stub: full listing deferred to a follow-up.
        return Response([])

    def create(self, request: Request) -> Response:
        # Stub: generation flow delegated to ReportGenerationService.
        return Response(
            {"detail": "report generation not yet wired to HTTP"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class AnalyticQueryViewSet(_TenantScopedMixin, viewsets.ViewSet):
    """Run a deterministic analytic query and optionally get an explanation."""

    def create(self, request: Request) -> Response:
        from apps.reporting.services.analytics import analytics_service

        tenant_id = self._tenant_id(request)
        kind = request.data.get("kind")
        parameters = request.data.get("parameters", {})
        question = request.data.get("natural_language_question")
        with_explanation = bool(request.data.get("with_explanation", True))

        # Build a transient AnalyticQuery (not persisted) for the runner.
        from apps.reporting.models import AnalyticQuery, QueryKind

        query = AnalyticQuery(
            tenant_id=tenant_id,
            kind=kind,
            parameters=parameters,
            natural_language_question=question or "",
        )
        try:
            insight = analytics_service.generate_insight(
                tenant_id=tenant_id,
                query=query,
                with_explanation=with_explanation,
                natural_language_question=question,
            )
        except ReportParametersInvalidError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("analytic query failed")
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "guid": str(insight.guid),
                "status": insight.status,
                "evidence": insight.evidence,
                "narrative": insight.narrative,
                "llm_provider": insight.llm_provider,
                "llm_model": insight.llm_model,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------


class DashboardViewSet(_TenantScopedMixin, viewsets.ViewSet):
    """CRUD dashboards and their widgets."""

    def list(self, request: Request) -> Response:  # noqa: A003
        # Stub.
        return Response([])

    def create(self, request: Request) -> Response:
        # Stub.
        return Response(
            {"detail": "dashboard creation not yet wired to HTTP"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=["post"], url_path="widgets")
    def add_widget(self, request: Request, pk: str | None = None) -> Response:
        # Stub.
        return Response(
            {"detail": "widget add not yet wired to HTTP"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
