"""
Lot model - groups splits for inventory/stock tracking.

Implements:
- BR-LOT-001: Lot closure criterion (balance = exactly zero)
- BR-LOT-002: Lot balance cached closure flag
"""

import uuid
from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce


class Lot(models.Model):
    """
    Groups splits for inventory/stock tracking.

    A lot is closed when its balance equals exactly zero.

    Attributes:
        guid: UUID primary key
        title: Lot title
        notes: Lot notes
        is_closed: Whether the lot is closed (balance = 0)
        account: Account this lot belongs to
        invoice: Linked invoice (if any)
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    is_closed = models.BooleanField(default=False, db_index=True)

    account = models.ForeignKey(
        "accounting_engine.Account",
        on_delete=models.CASCADE,
        related_name="lots",
    )
    invoice = models.ForeignKey(
        "business_documents.AccountingDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lots",
    )

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="lots",
        db_index=True,
    )
    legal_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="lots",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        indexes = [
            models.Index(fields=["account", "is_closed"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def balance(self) -> Decimal:
        """
        BR-LOT-001: Calculate lot balance.

        Sum of all split amounts in this lot.
        """
        total = self.lines.aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00"))
        )["total"]
        return total

    @property
    def value(self) -> Decimal:
        """Calculate lot value (in transaction currency)."""
        total = self.lines.aggregate(
            total=Coalesce(Sum("value"), Decimal("0.00"))
        )["total"]
        return total

    def check_closure(self) -> bool:
        """
        BR-LOT-001: Check if lot is closed.

        A lot is closed if and only if the sum of adjusted split amounts
        equals exactly zero.

        BR-LOT-002: If closure status is unknown, compute balance first.
        """
        current_balance = self.balance
        is_closed = (current_balance == Decimal("0.00"))

        if self.is_closed != is_closed:
            self.is_closed = is_closed
            self.save(update_fields=["is_closed"])

        return is_closed

    def add_line(self, journal_line) -> None:
        """Add a journal line to this lot."""
        journal_line.lot = self
        journal_line.save(update_fields=["lot"])

        # Re-check closure
        self.check_closure()

    def remove_line(self, journal_line) -> None:
        """Remove a journal line from this lot."""
        journal_line.lot = None
        journal_line.save(update_fields=["lot"])

        # Re-check closure
        self.check_closure()
