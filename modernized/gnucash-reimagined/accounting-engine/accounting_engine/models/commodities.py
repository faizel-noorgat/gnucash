"""
Commodity and Currency models.

Implements the multi-currency semantics defined in Spike 2 (ADR-009):
- Dual-field amount/value model
- Each Account has a commodity
- Transaction currency is explicit (not derived)
- ExchangeRate stores historical rates with daily granularity
"""

import uuid
from decimal import Decimal

from django.db import models


class CommodityNamespace(models.TextChoices):
    """Namespace for commodities."""

    CURRENCY = "CURRENCY", "Currency"
    SECURITY = "SECURITY", "Security"
    CRYPTOCURRENCY = "CRYPTO", "Cryptocurrency"


class Commodity(models.Model):
    """
    Anything tradable - currencies, securities, cryptocurrencies.

    Attributes:
        guid: UUID primary key
        namespace: CURRENCY, SECURITY, or CRYPTOCURRENCY
        mnemonic: Short code (e.g., USD, SGD, AAPL)
        fullname: Full name (e.g., US Dollar, Apple Inc.)
        cusip: CUSIP identifier for securities
        fraction: Smallest fraction (e.g., 100 for USD means 2 decimal places)
        quote_flag: Whether to fetch quotes for this commodity
        quote_source: Source for price quotes
        tenant: Multi-tenant isolation
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    namespace = models.CharField(max_length=20, choices=CommodityNamespace.choices)
    mnemonic = models.CharField(max_length=10, db_index=True)
    fullname = models.CharField(max_length=255)
    cusip = models.CharField(max_length=20, blank=True, null=True)
    fraction = models.IntegerField(default=100)  # 100 = 2 decimal places
    quote_flag = models.BooleanField(default=False)
    quote_source = models.CharField(max_length=50, blank=True, null=True)
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="commodities",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        unique_together = ["namespace", "mnemonic", "tenant"]
        indexes = [
            models.Index(fields=["namespace", "mnemonic"]),
        ]

    def __str__(self) -> str:
        return f"{self.mnemonic} ({self.get_namespace_display()})"

    @property
    def decimal_places(self) -> int:
        """Calculate decimal places from fraction."""
        if self.fraction <= 1:
            return 0
        return len(str(self.fraction - 1))

    def round_amount(self, amount: Decimal) -> Decimal:
        """Round amount to commodity precision using ROUND_HALF_UP."""
        return amount.quantize(Decimal(10) ** -self.decimal_places)


class Currency(Commodity):
    """
    Proxy model for currency-specific operations.

    Currencies are commodities with namespace=CURRENCY.
    """

    class Meta:
        proxy = True
        app_label = "accounting_engine"

    def save(self, *args, **kwargs):
        self.namespace = CommodityNamespace.CURRENCY
        super().save(*args, **kwargs)


class ExchangeRate(models.Model):
    """
    Historical exchange rate between two commodities.

    Stores rates with daily granularity. Multiple sources allowed.

    Attributes:
        from_commodity: Source commodity
        to_commodity: Target commodity
        rate_date: Date of the rate
        rate: Exchange rate (1 from_commodity = rate to_commodity)
        source: Source of the rate (e.g., ECB, Bloomberg, manual)
        tenant: Multi-tenant isolation
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_commodity = models.ForeignKey(
        Commodity,
        on_delete=models.CASCADE,
        related_name="outgoing_rates",
    )
    to_commodity = models.ForeignKey(
        Commodity,
        on_delete=models.CASCADE,
        related_name="incoming_rates",
    )
    rate_date = models.DateField(db_index=True)
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    source = models.CharField(max_length=50, default="manual")
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="exchange_rates",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "accounting_engine"
        unique_together = ["from_commodity", "to_commodity", "rate_date", "source"]
        indexes = [
            models.Index(fields=["from_commodity", "to_commodity", "rate_date"]),
            models.Index(fields=["rate_date"]),
        ]
        ordering = ["-rate_date"]

    def __str__(self) -> str:
        return f"{self.from_commodity.mnemonic} → {self.to_commodity.mnemonic}: {self.rate} on {self.rate_date}"

    @classmethod
    def get_rate(
        cls,
        from_commodity: Commodity,
        to_commodity: Commodity,
        rate_date,
        tenant,
    ) -> "ExchangeRate | None":
        """
        Get exchange rate for a specific date with fallback logic.

        Priority:
        1. Exact date match
        2. Most recent rate before the date
        3. None if no rate found

        BR-FX-001: Price lookup nearest-in-time
        """
        if from_commodity == to_commodity:
            # Same commodity, rate is 1:1
            return None

        # Try exact date first
        rate = cls.objects.filter(
            from_commodity=from_commodity,
            to_commodity=to_commodity,
            rate_date=rate_date,
            tenant=tenant,
        ).first()

        if rate:
            return rate

        # Try most recent rate before the date
        rate = cls.objects.filter(
            from_commodity=from_commodity,
            to_commodity=to_commodity,
            rate_date__lte=rate_date,
            tenant=tenant,
        ).order_by("-rate_date").first()

        return rate
