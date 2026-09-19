"""
Pytest configuration for business documents tests.

Django settings for this suite come from the unified project
(DJANGO_SETTINGS_MODULE=config.settings.test via pyproject.toml). This module
deliberately does no Django settings configuration and no app-registry
bootstrap: doing so here would clobber the unified project settings at
pytest collection time and break the rest of the test tree.
"""
import pytest


@pytest.fixture
def api_client():
    """Provide API client for tests"""
    from rest_framework.test import APIClient
    return APIClient()
