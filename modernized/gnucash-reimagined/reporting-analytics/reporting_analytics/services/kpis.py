"""Pre-built KPI functions used by dashboard widgets.

Each function is a pure read-only query against the Accounting Engine's
ledger. The output shape is a simple dict of name → (value, unit) pairs.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class KPIValue:
    name: str
    value: Decimal | float | int
    unit: str
    as_of: dt.date


def cash_balance(*, tenant_id: str, as_of: dt.date) -> list[KPIValue]:
    """Sum of all BANK and CASH account balances as of ``as_of``."""
    # Stub — real implementation would query accounting_engine_account.
    return [KPIValue(name="cash_balance", value=Decimal("0"), unit="SGD", as_of=as_of)]


def outstanding_receivables(
    *, tenant_id: str, as_of: dt.date
) -> list[KPIValue]:
    """Sum of unpaid customer invoices as of ``as_of``."""
    return [
        KPIValue(
            name="outstanding_receivables",
            value=Decimal("0"),
            unit="SGD",
            as_of=as_of,
        )
    ]


def outstanding_payables(*, tenant_id: str, as_of: dt.date) -> list[KPIValue]:
    """Sum of unpaid supplier bills as of ``as_of``."""
    return [
        KPIValue(
            name="outstanding_payables",
            value=Decimal("0"),
            unit="SGD",
            as_of=as_of,
        )
    ]


def monthly_revenue(
    *, tenant_id: str, year: int, month: int
) -> list[KPIValue]:
    """Total income for a given calendar month."""
    as_of = dt.date(year, month, 1)
    return [
        KPIValue(
            name="monthly_revenue",
            value=Decimal("0"),
            unit="SGD",
            as_of=as_of,
        )
    ]


# Registry for the dashboard widget renderer.
KPI_REGISTRY: dict[str, Any] = {
    "cash_balance": cash_balance,
    "outstanding_receivables": outstanding_receivables,
    "outstanding_payables": outstanding_payables,
    "monthly_revenue": monthly_revenue,
}
