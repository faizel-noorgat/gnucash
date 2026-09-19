from django.apps import AppConfig


class DomainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'identity_access.domain'
    label = 'domain'
    verbose_name = 'Identity & Access Domain'
