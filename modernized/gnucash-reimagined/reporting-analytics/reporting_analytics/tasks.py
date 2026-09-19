"""Celery tasks for reporting_analytics.

Tasks are thin wrappers around the service layer. They:

1. Load the relevant model instance.
2. Call the service function.
3. Handle errors and update the instance state.

All tasks are idempotent: re-running a task with the same input produces
the same output. The service layer enforces idempotency via state
transitions (e.g. a ReportInstance can only move from ``pending`` to
``running`` once).
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from .middleware import tenant_scope
from .models import AnalyticInsight, AnalyticQuery, ReportInstance
from .services import ai_explainer, analytics_engine, report_generator

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_report(self, instance_guid: str) -> None:
    """Generate a report instance.

    The task loads the instance, establishes the tenant scope, and
    delegates to ``report_generator.generate_report``.
    """
    try:
        instance = ReportInstance.objects.select_related("definition").get(
            guid=instance_guid
        )
    except ReportInstance.DoesNotExist:
        logger.error("ReportInstance %s not found", instance_guid)
        return

    tenant_id = str(instance.tenant_id)
    with tenant_scope(tenant_id):
        try:
            report_generator.generate_report(tenant_id=tenant_id, instance=instance)
        except Exception as exc:
            logger.exception("report generation failed")
            raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_analytic_query(self, query_guid: str) -> None:
    """Run an analytic query and produce an insight.

    The task:

    1. Loads the ``AnalyticQuery``.
    2. Runs the deterministic runner to produce metrics + evidence.
    3. If evidence is present, calls the AI explainer.
    4. Persists an ``AnalyticInsight``.
    """
    try:
        query = AnalyticQuery.objects.get(guid=query_guid)
    except AnalyticQuery.DoesNotExist:
        logger.error("AnalyticQuery %s not found", query_guid)
        return

    tenant_id = str(query.tenant_id)
    with tenant_scope(tenant_id):
        try:
            result = analytics_engine.run_analytic_query(
                tenant_id=tenant_id, query=query
            )
        except Exception as exc:
            logger.exception("analytic query failed")
            raise self.retry(exc=exc)

        # Persist the metrics on the query.
        query.metrics = result.metrics_dict()
        query.save(update_fields=["metrics", "executed_query"])

        # Only produce an insight if we have evidence.
        if not result.evidence:
            logger.info(
                "analytic query %s produced no evidence; skipping insight",
                query_guid,
            )
            return

        try:
            explanation = ai_explainer.explain(
                result=result,
                natural_language_question=query.natural_language_question,
            )
        except Exception:
            logger.exception("AI explainer failed; insight will have no narrative")
            explanation = None

        AnalyticInsight.objects.create(
            tenant_id=tenant_id,
            query=query,
            status="generated",
            evidence=[e.as_dict() for e in result.evidence],
            narrative=explanation.narrative if explanation else "",
            llm_provider=explanation.provider if explanation else "",
            llm_model=explanation.model if explanation else "",
            confidence_score=explanation.confidence_score if explanation else None,
        )


@shared_task
def refresh_dashboard_tile(dashboard_guid: str, widget_guid: str) -> dict:
    """Refresh a single dashboard widget's cached data.

    Returns the refreshed data; the view layer is responsible for
    caching it in Redis with the widget's ``cache_ttl_seconds``.
    """
    from .models import DashboardWidget
    from .services import kpis

    try:
        widget = DashboardWidget.objects.get(guid=widget_guid)
    except DashboardWidget.DoesNotExist:
        logger.error("DashboardWidget %s not found", widget_guid)
        return {}

    if widget.widget_type == "kpi" and widget.kpi_name:
        fn = kpis.KPI_REGISTRY.get(widget.kpi_name)
        if fn is None:
            return {"error": f"unknown kpi {widget.kpi_name!r}"}
        values = fn(
            tenant_id=str(widget.dashboard.tenant_id),
            **widget.parameters,
        )
        return {
            "widget": str(widget.guid),
            "values": [
                {"name": v.name, "value": str(v.value), "unit": v.unit}
                for v in values
            ],
        }
    return {"widget": str(widget.guid), "values": []}
