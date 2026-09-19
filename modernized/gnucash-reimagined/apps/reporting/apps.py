"""
Reporting & Analytics bounded context.

Owns: report definitions, deterministic report queries, dashboards,
      analytic queries, AI explanations/insights
"""

from django.apps import AppConfig


class ReportingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reporting"
    label = "reporting"
    verbose_name = "Reporting & Analytics"
