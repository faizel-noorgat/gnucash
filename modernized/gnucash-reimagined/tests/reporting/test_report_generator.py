"""Unit tests for the report generator service."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import pytest

from apps.reporting.exceptions import (
    ReportDefinitionNotFoundError,
    ReportParametersInvalidError,
)
from apps.reporting.models import ReportDefinition, ReportType
from apps.reporting.services.reports import (
    ReportParameters,
    get_generator,
    validate_parameters,
)


def test_validate_parameters_parses_iso_dates():
    definition = ReportDefinition(
        guid=uuid.uuid4(),
        code="trial_balance",
        name="Trial Balance",
        report_type=ReportType.TRIAL_BALANCE,
    )
    params = validate_parameters(
        definition,
        {"date_from": "2026-01-01", "date_to": "2026-09-19"},
    )
    assert params.date_from == dt.date(2026, 1, 1)
    assert params.date_to == dt.date(2026, 9, 19)


def test_validate_parameters_rejects_invalid_date_order():
    definition = ReportDefinition(
        guid=uuid.uuid4(),
        code="trial_balance",
        name="Trial Balance",
        report_type=ReportType.TRIAL_BALANCE,
    )
    with pytest.raises(ReportParametersInvalidError):
        validate_parameters(
            definition,
            {"date_from": "2026-12-31", "date_to": "2026-01-01"},
        )


def test_validate_parameters_rejects_malformed_date():
    definition = ReportDefinition(
        guid=uuid.uuid4(),
        code="trial_balance",
        name="Trial Balance",
        report_type=ReportType.TRIAL_BALANCE,
    )
    with pytest.raises(ReportParametersInvalidError):
        validate_parameters(
            definition,
            {"date_from": "not-a-date", "date_to": "2026-09-19"},
        )


def test_get_generator_returns_registered_function():
    gen = get_generator("trial_balance")
    assert callable(gen)


def test_get_generator_raises_for_unknown_code():
    with pytest.raises(ReportDefinitionNotFoundError):
        get_generator("nonexistent_report")


def test_report_parameters_are_frozen():
    params = ReportParameters(
        date_from=dt.date(2026, 1, 1),
        date_to=dt.date(2026, 9, 19),
    )
    with pytest.raises(AttributeError):
        params.date_from = dt.date(2026, 2, 1)  # type: ignore[misc]
