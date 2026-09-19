"""Test fixtures for reporting_analytics."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def tenant_id() -> str:
    """A stable tenant id for tests."""
    return "tenant-test-0001"


@pytest.fixture
def other_tenant_id() -> str:
    """A different tenant id for isolation tests."""
    return "tenant-test-0002"


@pytest.fixture
def user(db, tenant_id: str):
    """A test user."""
    return User.objects.create_user(
        username=f"testuser-{tenant_id}",
        email=f"test@{tenant_id}.example.com",
        password="test-password",
    )


@pytest.fixture
def today() -> dt.date:
    return dt.date(2026, 9, 19)


@pytest.fixture
def date_range(today: dt.date) -> tuple[dt.date, dt.date]:
    return dt.date(2026, 1, 1), today


@pytest.fixture
def mock_llm_provider():
    """A mock LLM provider that returns canned narratives."""
    from reporting_analytics.services.ai_explainer import StubExplainer

    return StubExplainer()
