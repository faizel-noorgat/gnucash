from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'identity_access.api'
    label = 'api'
    verbose_name = 'Identity & Access API'
