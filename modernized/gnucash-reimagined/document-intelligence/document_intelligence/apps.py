"""Django application configuration for Document Intelligence."""

from django.apps import AppConfig


class DocumentIntelligenceConfig(AppConfig):
    """Document Intelligence app configuration."""

    name = "document_intelligence"
    verbose_name = "Document Intelligence"
    default_auto_field = "django.db.models.UUIDField"

    def ready(self) -> None:
        """Run ready-time initialization.

        - Register signals (if any)
        - Import checks module so system checks run on startup
        """
        from . import checks  # noqa: F401  (registers system checks)
