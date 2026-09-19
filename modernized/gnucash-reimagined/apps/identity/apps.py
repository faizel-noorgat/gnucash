"""
Identity & Access Django App Configuration

Registers the identity app with Django's app registry.
The User model provided by this app is configured as the project's
custom user model via AUTH_USER_MODEL = "identity.User".
"""

from django.apps import AppConfig


class IdentityConfig(AppConfig):
    """Django app configuration for the Identity & Access bounded context."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.identity'
    label = 'identity'
    verbose_name = 'Identity & Access'

    def ready(self):
        """App initialization hook.

        Import signal handlers or perform any startup tasks here.
        Currently a no-op stub.
        """
        pass
