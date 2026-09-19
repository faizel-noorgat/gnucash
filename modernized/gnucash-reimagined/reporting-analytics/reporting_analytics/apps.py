"""Django AppConfig for reporting_analytics."""

from django.apps import AppConfig


class ReportingAnalyticsConfig(AppConfig):
    name = "reporting_analytics"
    verbose_name = "Reporting & Analytics"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        # Import signal handlers / Celery task autodiscovery.
        from . import tasks as _tasks  # noqa: F401

        _ = _tasks
