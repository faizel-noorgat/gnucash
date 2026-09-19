"""Django app configuration for accounting-engine."""

from django.apps import AppConfig


class AccountingEngineConfig(AppConfig):
    """Configuration for the accounting engine app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounting_engine"
    verbose_name = "Accounting Engine"

    def ready(self):
        """Perform app initialization."""
        # Import signal handlers if any
        pass
