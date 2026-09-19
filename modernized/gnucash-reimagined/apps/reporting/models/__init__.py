"""Models package for the Reporting & Analytics bounded context."""

from .analytics import AnalyticInsight, AnalyticQuery, InsightStatus, QueryKind
from .dashboards import Dashboard, DashboardWidget, WidgetType
from .reports import (
    OutputFormat,
    ReportDefinition,
    ReportInstance,
    ReportStatus,
    ReportType,
)

__all__ = [
    # reports
    "ReportDefinition",
    "ReportInstance",
    "ReportStatus",
    "ReportType",
    "OutputFormat",
    # dashboards
    "Dashboard",
    "DashboardWidget",
    "WidgetType",
    # analytics
    "AnalyticQuery",
    "AnalyticInsight",
    "InsightStatus",
    "QueryKind",
]
