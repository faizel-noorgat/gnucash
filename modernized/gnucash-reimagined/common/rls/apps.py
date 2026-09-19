"""
App config for the RLS infrastructure app.

This app owns no models of its own - ``common/rls/models.py`` holds abstract
mixins only. It exists so that the RLS helper functions, the ``app_user`` role
and the per-table policies have a home in the migration graph, which is what
makes a clean deployment receive them deterministically instead of depending on
``docker/init-db.sql`` being run by hand.
"""

from django.apps import AppConfig


class RlsConfig(AppConfig):
    """Configuration for the row-level-security infrastructure app."""

    name = "common.rls"
    label = "rls"
    verbose_name = "Row Level Security"
    default_auto_field = "django.db.models.BigAutoField"
