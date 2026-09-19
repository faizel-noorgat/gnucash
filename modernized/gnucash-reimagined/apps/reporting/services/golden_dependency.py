"""Golden-test dependency gate for the reporting context.

The Reporting & Analytics bounded context is a *consumer* of the
Accounting Engine's ledger. Before a reporting test that touches posted
financial data can be considered valid, the Accounting Engine's
**golden accounting tests** (double-entry balancing, multi-currency
semantics, trading-account balancing, reconciliation, reversal/
correcting entries) must be green.

This module implements the gate:

* ``is_golden_green(manifest_path)`` — returns True if the manifest
  file exists and contains ``status=green``.
* ``require_golden(manifest_path)`` — raises ``GoldenTestsNotGreen``
  if the manifest is missing or not green.

The gate is invoked by the pytest plugin (see the reporting conftest)
and by the CI pipeline before running the reporting acceptance suite.
Tests that depend on it are marked ``@pytest.mark.golden_dependency``.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class GoldenTestsNotGreen(Exception):
    """Raised when the accounting-engine golden tests are not green."""


def is_golden_green(manifest_path: Path) -> bool:
    """Return True if the golden manifest exists and is green."""
    if not manifest_path.exists():
        logger.warning("golden manifest not found at %s", manifest_path)
        return False
    content = manifest_path.read_text()
    return "status=green" in content


def require_golden(manifest_path: Path) -> None:
    """Raise if the golden manifest is not green."""
    if not is_golden_green(manifest_path):
        raise GoldenTestsNotGreen(
            f"accounting-engine golden tests are not green; "
            f"refusing to run reporting tests that depend on posted data. "
            f"Manifest path: {manifest_path}"
        )


__all__ = [
    "GoldenTestsNotGreen",
    "is_golden_green",
    "require_golden",
]
