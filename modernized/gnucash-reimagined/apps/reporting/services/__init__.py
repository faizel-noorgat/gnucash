"""Services package — business logic for the Reporting & Analytics context.

Three services own the three verticals of the bounded context:

* ``report_service`` (``ReportGenerationService``) — deterministic
  report generation (trial balance, balance sheet, income statement,
  cash flow, …). Reads only from the Accounting Engine.
* ``analytics_service`` (``AnalyticsService``) — deterministic
  analytic queries + evidence gate + optional LLM explanation.
* ``dashboard_service`` (``DashboardService``) — dashboard / widget
  CRUD and rendering orchestration.

No arithmetic is ever delegated to the LLM. The AI layer is given
*metrics + evidence* produced here and may only produce a narrative
that references them.
"""

from .analytics import AnalyticsService, analytics_service
from .dashboards import DashboardService, dashboard_service
from .reports import ReportGenerationService, report_service

__all__ = [
    "ReportGenerationService",
    "report_service",
    "AnalyticsService",
    "analytics_service",
    "DashboardService",
    "dashboard_service",
]
