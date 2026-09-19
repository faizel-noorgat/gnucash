from django.apps import AppConfig


class BusinessDocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'business_documents'
    verbose_name = 'Business Documents'

    def ready(self):
        # Import signal handlers if needed
        pass
