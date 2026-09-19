"""Report API views."""

from __future__ import annotations

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ..middleware import get_current_tenant_id
from ..models import ReportDefinition, ReportInstance
from ..serializers.reports import (
    ReportDefinitionSerializer,
    ReportInstanceSerializer,
)
from ..services import report_generator
from ..tasks import generate_report as generate_report_task


class ReportDefinitionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """List and retrieve report definitions.

    Definitions are scoped to the current tenant.
    """

    serializer_class = ReportDefinitionSerializer

    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        return ReportDefinition.objects.filter(tenant_id=tenant_id)


class ReportInstanceViewSet(viewsets.ModelViewSet):
    """Create, list, retrieve, and cancel report instances.

    POST creates a new instance in ``pending`` state and enqueues a
    Celery task to generate the report. The client polls GET until
    ``status`` transitions to ``succeeded`` or ``failed``.
    """

    serializer_class = ReportInstanceSerializer

    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        return ReportInstance.objects.filter(tenant_id=tenant_id)

    def perform_create(self, serializer):
        tenant_id = get_current_tenant_id()
        definition = ReportDefinition.objects.get(
            guid=serializer.validated_data["definition_id"],
            tenant_id=tenant_id,
        )
        instance = serializer.save(
            tenant_id=tenant_id,
            definition=definition,
            requested_by=self.request.user if self.request.user.is_authenticated else None,
        )
        # Enqueue the async generation task.
        generate_report_task.delay(str(instance.guid))

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        """Cancel a pending or running report."""
        instance = self.get_object()
        try:
            instance.transition_to("cancelled")
            instance.save(update_fields=["status"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["get"])
    def result(self, request: Request, pk: str | None = None) -> Response:
        """Return the result rows of a succeeded report."""
        instance = self.get_object()
        if instance.status != "succeeded":
            return Response(
                {"detail": f"report is not yet succeeded (status={instance.status})"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {
                "definition_code": instance.definition.code,
                "parameters": instance.parameters,
                "columns": list(instance.result_rows[0].keys()) if instance.result_rows else [],
                "rows": instance.result_rows,
                "row_count": instance.row_count,
                "generated_at": instance.completed_at,
            }
        )
