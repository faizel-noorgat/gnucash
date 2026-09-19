"""Reporting & Analytics API URL configuration.

Routes are registered under the ``reporting/`` prefix by the project
root URLconf. Each viewset is wired to a DRF router in production;
this stub uses explicit ``path()`` entries so the URL surface is
visible without importing a router.
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "reporting"

urlpatterns = [
    # Report definitions (list / retrieve).
    path(
        "definitions/",
        views.ReportDefinitionViewSet.as_view({"get": "list"}),
        name="report-definition-list",
    ),
    path(
        "definitions/<str:pk>/",
        views.ReportDefinitionViewSet.as_view({"get": "retrieve"}),
        name="report-definition-detail",
    ),
    # Report instances (create / list).
    path(
        "instances/",
        views.ReportInstanceViewSet.as_view({"get": "list", "post": "create"}),
        name="report-instance-list",
    ),
    # Analytic queries (run a query + optional explanation).
    path(
        "analytics/",
        views.AnalyticQueryViewSet.as_view({"post": "create"}),
        name="analytic-query-create",
    ),
    # Dashboards.
    path(
        "dashboards/",
        views.DashboardViewSet.as_view({"get": "list", "post": "create"}),
        name="dashboard-list",
    ),
    path(
        "dashboards/<str:pk>/widgets/",
        views.DashboardViewSet.as_view({"post": "add_widget"}),
        name="dashboard-add-widget",
    ),
]
