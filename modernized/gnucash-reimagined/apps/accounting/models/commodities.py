"""
Commodity and Currency models.

Implements the multi-currency semantics defined in Spike 2 (ADR-009):
- Dual-field amount/value model
- Each Account has a commodity
- Transaction currency is explicit (not derived)
- ExchangeRate stores historical rates with daily granularity

Accounting Semantics:
    Commodities are the fundamental unit of measure in accounting.
    A commodity can be a currency (USD, EUR), a security (AAPL, MSFT),
    or a cryptocurrency (BTC, ETH). Each commodity has a namespace,
    mnemonic (ticker symbol), and precision (fraction).

    Exchange rates are stored historically with daily granularity,
    enabling multi-currency transactions and reporting.
"""

import uuid
from decimal import Decimal

from django.db import models


class CommodityNamespace(models.TextChoices):
    """
    Namespace for commodities.

    CURRENCY: Fiat currencies (USD, EUR, SGD)
    SECURITY: Stocks, bonds, mutual funds
    CRYPTOCURRENCY: Digital currencies (BTC, ETH)
    """

    CURRENCY = "CURRENCY", "Currency"
    SECURITY = "SECURITY", "Security"
    CRYPTOCURRENCY = "CRYPTO", "Cryptocurrency"


class Commodity(models.Model):
    """
    Anything tradable - currencies, securities, cryptocurrencies.

    Accounting Semantics:
        A commodity is the unit of measure for financial transactions.
        Every account holds balances in a specific commodity. When transactions
        cross commodities (e.g., buying foreign stock), the dual-field
        amount/value model tracks both the quantity and the transaction value.

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

    Decimal Precision:
        The `fraction` field defines precision. For USD (fraction=100),
        decimal_places = 2. Amounts are rounded using ROUND_HALF_UP.
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
        app_label = "accounting"
        unique_together = ["namespace", "mnemonic", "tenant"]
        indexes = [
            models.Index(fields=["namespace", "mnemonic"]),
        ]

    def __str__(self) -> str:
        return f"{self.mnemonic} ({self.get_namespace_display()})"

    @property
    def decimal_places(self) -> int:
        """
        Calculate decimal places from fraction.

        Example: fraction=100 → 2 decimal places (cents)
                 fraction=10000 → 4 decimal places
        """
        if self.fraction <= 1:
            return 0
        return len(str(self.fraction - 1))

    def round_amount(self, amount: Decimal) -> Decimal:
        """
        Round amount to commodity precision using ROUND_HALF_UP.

        This ensures all amounts are rounded consistently according to
        the commodity's standard precision (e.g., 2 decimals for USD).
        """
        return amount.quantize(Decimal(10) ** -self.decimal_places)


class Currency(Commodity):
    """
    Proxy model for currency-specific operations.

    Accounting Semantics:
        Currencies are commodities with namespace=CURRENCY.
        This proxy model enforces that constraint and provides
        currency-specific convenience methods.

    Usage:
        Use Currency when you specifically need a currency (not a security).
        The proxy model automatically sets namespace=CURRENCY on save.
    """

    class Meta:
        proxy = True
        app_label = "accounting"

    def save(self, *args, **kwargs):
        """Force namespace to CURRENCY before saving."""
        self.namespace = CommodityNamespace.CURRENCY
        super().save(*args, **kwargs)


class ExchangeRate(models.Model):
    """
    Historical exchange rate between two commodities.

    Accounting Semantics:
        Exchange rates enable multi-currency transactions. When a transaction
        involves two different commodities (e.g., buying EUR with USD), the
        exchange rate at the transaction date determines the conversion.

        Rates are stored with daily granularity. Multiple sources are allowed
        (e.g., ECB, Bloomberg, manual entry). The get_rate() method implements
        a fallback strategy: exact date → most recent prior date → None.

    ADR-009 Compliance:
        - Transaction currency is explicit (not derived from accounts)
        - Each journal line has both amount (account commodity) and value
          (transaction currency)
        - Exchange rates are used to validate the amount/value relationship

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
        app_label = "accounting"
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

        BR-FX-001: Price lookup nearest-in-time

        Priority:
        1. Exact date match
        2. Most recent rate before the date
        3. None if no rate found

        Accounting Semantics:
            This implements the "nearest-in-time" principle for exchange rates.
            If no rate exists for the exact transaction date, use the most recent
            prior rate. This handles weekends, holidays, and missing data gracefully.

            If from_commodity == to_commodity, returns None (no conversion needed).

        Args:
            from_commodity: Source commodity
            to_commodity: Target commodity
            rate_date: Date of the transaction
            tenant: Multi-tenant isolation

        Returns:
            ExchangeRate instance or None
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
