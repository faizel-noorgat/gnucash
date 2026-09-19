"""Root conftest for reporting_analytics tests.

Fixtures defined here are shared across all test modules.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import pytest
from django.conf import settings


@pytest.fixture
def tenant_id() -> str:
    """A stable tenant id for unit tests."""
    return "tenant-test-0001"


@pytest.fixture
def user_id() -> str:
    """A stable user id for unit tests."""
    return "user-test-0001"


@pytest.fixture
def today() -> dt.date:
    return dt.date(2026, 9, 19)


@pytest.fixture
def date_range(today: dt.date) -> tuple[dt.date, dt.date]:
    return dt.date(2026, 1, 1), today
