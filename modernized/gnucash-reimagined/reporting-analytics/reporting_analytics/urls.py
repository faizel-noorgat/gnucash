"""URL configuration for reporting_analytics."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.analytics import AnalyticInsightViewSet, AnalyticQueryViewSet
from .views.dashboards import DashboardViewSet
from .views.reports import ReportDefinitionViewSet, ReportInstanceViewSet

router = DefaultRouter()
router.register(r"report-definitions", ReportDefinitionViewSet, basename="report-definition")
router.register(r"report-instances", ReportInstanceViewSet, basename="report-instance")
router.register(r"analytic-queries", AnalyticQueryViewSet, basename="analytic-query")
router.register(r"analytic-insights", AnalyticInsightViewSet, basename="analytic-insight")
router.register(r"dashboards", DashboardViewSet, basename="dashboard")

app_name = "reporting_analytics"

urlpatterns = [
    path("", include(router.urls)),
]
