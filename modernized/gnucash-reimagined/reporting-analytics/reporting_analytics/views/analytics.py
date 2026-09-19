"""Analytics API views."""

from __future__ import annotations

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ..middleware import get_current_tenant_id
from ..models import AnalyticInsight, AnalyticQuery
from ..serializers.analytics import (
    AnalyticInsightSerializer,
    AnalyticQuerySerializer,
)
from ..services import ai_explainer, analytics_engine
from ..tasks import run_analytic_query as run_analytic_query_task


class AnalyticQueryViewSet(viewsets.ModelViewSet):
    """Create and list analytic queries.

    POST creates a new query and enqueues a Celery task to run it.
    The task produces metrics + evidence, then optionally calls the
    AI explainer to produce a narrative.
    """

    serializer_class = AnalyticQuerySerializer

    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        return AnalyticQuery.objects.filter(tenant_id=tenant_id)

    def perform_create(self, serializer):
        tenant_id = get_current_tenant_id()
        query = serializer.save(
            tenant_id=tenant_id,
            requested_by=self.request.user if self.request.user.is_authenticated else None,
        )
        run_analytic_query_task.delay(str(query.guid))


class AnalyticInsightViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """List and retrieve analytic insights.

    Insights are created by the analytic-query pipeline; this endpoint
    is read-only for the UI.
    """

    serializer_class = AnalyticInsightSerializer

    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        return AnalyticInsight.objects.filter(tenant_id=tenant_id)

    @action(detail=True, methods=["post"])
    def review(self, request: Request, pk: str | None = None) -> Response:
        """Mark an insight as reviewed or rejected."""
        insight = self.get_object()
        new_status = request.data.get("status")
        if new_status not in {"reviewed", "rejected"}:
            return Response(
                {"detail": "status must be 'reviewed' or 'rejected'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        insight.status = new_status
        insight.reviewed_by = request.user
        from django.utils import timezone

        insight.reviewed_at = timezone.now()
        insight.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return Response(self.get_serializer(insight).data)
