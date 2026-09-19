"""
Lot model - groups splits for inventory/stock tracking.

Implements:
- BR-LOT-001: Lot closure criterion (balance = exactly zero)
- BR-LOT-002: Lot balance cached closure flag

Accounting Semantics:
    Lots are used to track specific batches of inventory or securities.
    When goods are purchased, a lot is created. When goods are sold,
    the lot balance decreases. A lot is closed when its balance reaches zero.

    Lot tracking enables:
    - FIFO/LIFO inventory valuation
    - Capital gains calculation for securities
    - Batch-specific cost tracking
    - Inventory aging analysis

    Closure Criterion (BR-LOT-001):
    A lot is closed if and only if the sum of all split amounts equals exactly zero.
    The `is_closed` flag is cached for performance (BR-LOT-002).
"""

import uuid
from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce


class Lot(models.Model):
    """
    Groups splits for inventory/stock tracking.

    Accounting Semantics:
        A lot represents a specific batch of goods or securities.
        When inventory is purchased, a lot is created with a positive balance.
        When inventory is sold, the lot balance decreases (negative splits).
        When the balance reaches zero, the lot is closed.

        Lot tracking enables specific cost flow assumptions (FIFO, LIFO, specific identification).

    Attributes:
        guid: UUID primary key
        title: Lot title (e.g., "Purchase Order #1234")
        notes: Lot notes
        is_closed: Whether the lot is closed (balance = 0)
        account: Account this lot belongs to (e.g., Inventory account)
        invoice: Linked invoice (if any)
        tenant: Multi-tenant isolation
        legal_entity: Legal entity that owns this lot

    Closure Logic (BR-LOT-001, BR-LOT-002):
        A lot is closed when the sum of all split amounts equals exactly zero.
        The `is_closed` flag is cached and updated automatically when splits are added/removed.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    is_closed = models.BooleanField(default=False, db_index=True)

    account = models.ForeignKey(
        "accounting.Account",
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
        app_label = "accounting"
        indexes = [
            models.Index(fields=["account", "is_closed"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def balance(self) -> Decimal:
        """
        BR-LOT-001: Calculate lot balance.

        Accounting Semantics:
            Sum of all split amounts in this lot.
            Positive balance = goods in stock
            Zero balance = lot closed
            Negative balance = over-sold (should not happen in normal operation)

        Returns:
            Decimal balance in the account's commodity
        """
        total = self.lines.aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00"))
        )["total"]
        return total

    @property
    def value(self) -> Decimal:
        """
        Calculate lot value (in transaction currency).

        Accounting Semantics:
            This is the total cost/value of the lot in the transaction currency.
            Used for inventory valuation and cost of goods sold calculations.

        Returns:
            Decimal value in transaction currency
        """
        total = self.lines.aggregate(
            total=Coalesce(Sum("value"), Decimal("0.00"))
        )["total"]
        return total

    def check_closure(self) -> bool:
        """
        BR-LOT-001: Check if lot is closed.

        Accounting Semantics:
            A lot is closed if and only if the sum of adjusted split amounts
            equals exactly zero.

            BR-LOT-002: If closure status is unknown, compute balance first.
            The `is_closed` flag is cached for performance and updated here.

        Returns:
            True if closed, False otherwise
        """
        current_balance = self.balance
        is_closed = (current_balance == Decimal("0.00"))

        if self.is_closed != is_closed:
            self.is_closed = is_closed
            self.save(update_fields=["is_closed"])

        return is_closed

    def add_line(self, journal_line) -> None:
        """
        Add a journal line to this lot.

        Accounting Semantics:
            Links a journal line (split) to this lot for tracking.
            Used when goods are purchased (positive amount) or sold (negative amount).
            After adding, the closure status is re-checked.

        Args:
            journal_line: JournalLine instance to add to this lot
        """
        journal_line.lot = self
        journal_line.save(update_fields=["lot"])

        # Re-check closure
        self.check_closure()

    def remove_line(self, journal_line) -> None:
        """
        Remove a journal line from this lot.

        Accounting Semantics:
            Unlinks a journal line from this lot.
            Used when correcting inventory errors or reversing transactions.
            After removing, the closure status is re-checked.

        Args:
            journal_line: JournalLine instance to remove from this lot
        """
        journal_line.lot = None
        journal_line.save(update_fields=["lot"])

        # Re-check closure
        self.check_closure()
