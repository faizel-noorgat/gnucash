"""
Fiscal period model.

Implements period locking to prevent posting to closed periods.
"""

import uuid
from datetime import date
from typing import Optional

from django.db import models


class FiscalPeriodStatus(models.TextChoices):
    """Fiscal period status."""

    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    LOCKED = "locked", "Locked"


class FiscalPeriod(models.Model):
    """
    Fiscal period for period-end controls.

    Periods can be open, closed, or locked.
    Posting is only allowed to open periods.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=FiscalPeriodStatus.choices,
        default=FiscalPeriodStatus.OPEN,
        db_index=True,
    )
    fiscal_year = models.IntegerField(db_index=True)

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="fiscal_periods",
        db_index=True,
    )
    legal_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="fiscal_periods",
        db_index=True,
    )

    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        unique_together = ["start_date", "end_date", "legal_entity"]
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["tenant", "legal_entity", "status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_date} - {self.end_date})"

    @property
    def is_open(self) -> bool:
        """Check if period is open for posting."""
        return self.status == FiscalPeriodStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if period is closed."""
        return self.status == FiscalPeriodStatus.CLOSED

    @property
    def is_locked(self) -> bool:
        """Check if period is locked (cannot be reopened)."""
        return self.status == FiscalPeriodStatus.LOCKED

    def close(self, user=None):
        """Close the fiscal period."""
        if self.status != FiscalPeriodStatus.OPEN:
            raise ValueError("Can only close open periods.")

        from django.utils import timezone

        self.status = FiscalPeriodStatus.CLOSED
        self.closed_at = timezone.now()
        self.closed_by = user
        self.save()

    def lock(self, user=None):
        """Lock the fiscal period (permanent)."""
        self.status = FiscalPeriodStatus.LOCKED
        self.closed_at = self.closed_at or timezone.now()
        self.closed_by = user
        self.save()

    def reopen(self):
        """Reopen a closed period (only if not locked)."""
        if self.status == FiscalPeriodStatus.LOCKED:
            raise ValueError("Cannot reopen a locked period.")

        self.status = FiscalPeriodStatus.OPEN
        self.closed_at = None
        self.closed_by = None
        self.save()

    @classmethod
    def get_period_for_date(
        cls,
        tenant,
        legal_entity,
        transaction_date: date,
    ) -> Optional["FiscalPeriod"]:
        """Get the fiscal period for a given date."""
        return cls.objects.filter(
            tenant=tenant,
            legal_entity=legal_entity,
            start_date__lte=transaction_date,
            end_date__gte=transaction_date,
        ).first()
