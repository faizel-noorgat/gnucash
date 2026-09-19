"""Custom exception classes and DRF exception handler."""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ReportingAnalyticsError(Exception):
    """Base class for all reporting-analytics domain errors."""


class TenantRequiredError(ReportingAnalyticsError):
    """Raised when a query is attempted without a tenant context."""


class ReportDefinitionNotFoundError(ReportingAnalyticsError):
    """Raised when a report id has no matching definition."""


class ReportParametersInvalidError(ReportingAnalyticsError):
    """Raised when report parameters fail validation."""


class AccountingEngineUnavailableError(ReportingAnalyticsError):
    """Raised when the Accounting Engine cannot be reached."""


class LLMProviderError(ReportingAnalyticsError):
    """Raised when the configured LLM provider fails."""


class EvidenceMissingError(ReportingAnalyticsError):
    """Raised when an AI insight cannot be traced to concrete ledger rows.

    This is a safety error: if the deterministic query layer cannot produce
    evidence, the AI explainer must NOT fabricate an explanation. The
    caller should fall back to returning the raw metrics.
    """


def api_exception_handler(exc, context):  # type: ignore[no-untyped-def]
    """Map domain exceptions to sensible HTTP responses."""
    response = exception_handler(exc, context)
    if response is not None:
        return response

    mapping = {
        TenantRequiredError: status.HTTP_400_BAD_REQUEST,
        ReportDefinitionNotFoundError: status.HTTP_404_NOT_FOUND,
        ReportParametersInvalidError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        AccountingEngineUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
        LLMProviderError: status.HTTP_502_BAD_GATEWAY,
        EvidenceMissingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    for cls, code in mapping.items():
        if isinstance(exc, cls):
            logger.warning(
                "domain error: %s", exc, extra={"exc_type": cls.__name__}
            )
            return Response({"detail": str(exc)}, status=code)

    logger.exception("unhandled error in reporting-analytics")
    return Response(
        {"detail": "Internal server error."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
