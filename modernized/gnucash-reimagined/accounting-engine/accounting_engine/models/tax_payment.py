"""
Tax and Payment Term models.

Implements:
- BR-TAX-001: Tax table entry types (VALUE, PERCENT)
- BR-TAX-002: Tax-included price back-computation
- BR-TAX-003: Discount ordering modes (PRETAX, SAMETIME, POSTTAX)
- Versioned tax rules with effective dates
- frozen_tax_table_json snapshot at posting (ADR-010)
"""

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db import models


class TaxRuleType(models.TextChoices):
    """Tax calculation type."""

    VALUE = "VALUE", "Absolute Amount"
    PERCENT = "PERCENT", "Percentage"


class DiscountOrderingMode(models.IntegerChoices):
    """
    BR-TAX-003: Discount ordering modes.

    - PRETAX (1): discount on pretax, tax on (pretax - discount)
    - SAMETIME (2): discount on pretax, tax on pretax (ignoring discount)
    - POSTTAX (3): discount on (pretax + tax), tax on pretax
    """

    PRETAX = 1, "Pre-Tax"
    SAMETIME = 2, "Same Time"
    POSTTAX = 3, "Post-Tax"


class TaxRule(models.Model):
    """
    Versioned tax rule with effective dates.

    Attributes:
        guid: UUID primary key
        name: Tax rule name (e.g., "GST 9%")
        code: Tax code
        rule_type: VALUE or PERCENT
        rate: Tax rate (for PERCENT) or fixed amount (for VALUE)
        effective_from: When this rule becomes effective
        effective_to: When this rule expires (null = still active)
        account: Tax account for posting
        tenant: Multi-tenant isolation
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, db_index=True)
    rule_type = models.CharField(
        max_length=20,
        choices=TaxRuleType.choices,
    )
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Tax rate (for PERCENT) or fixed amount (for VALUE)",
    )
    effective_from = models.DateField(db_index=True)
    effective_to = models.DateField(null=True, blank=True)

    account = models.ForeignKey(
        "accounting_engine.Account",
        on_delete=models.PROTECT,
        related_name="tax_rules",
    )

    is_active = models.BooleanField(default=True, db_index=True)

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="tax_rules",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        ordering = ["-effective_from"]
        indexes = [
            models.Index(fields=["code", "effective_from"]),
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.name}"

    @classmethod
    def get_applicable_rate(
        cls,
        tenant,
        tax_code: str,
        transaction_date,
    ) -> Optional["TaxRule"]:
        """Get the applicable tax rule for a given date."""
        from django.db.models import Q

        return cls.objects.filter(
            tenant=tenant,
            code=tax_code,
            is_active=True,
            effective_from__lte=transaction_date,
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=transaction_date)
        ).order_by("-effective_from").first()

    def calculate_tax(
        self,
        base_amount: Decimal,
        fraction: int = 100,
    ) -> Decimal:
        """
        Calculate tax amount for a given base amount.

        BR-TAX-001: Tax table entry types
        - VALUE: Fixed amount
        - PERCENT: Percentage of base

        BR-TAX-002: Tax-included price back-computation
        If tax is included in the price:
        pretax = (aggregate - tvalue) / (1 + tpercent)
        """
        decimal_places = len(str(fraction - 1))

        if self.rule_type == TaxRuleType.VALUE:
            return self.rate.quantize(Decimal(10) ** -decimal_places, rounding=ROUND_HALF_UP)
        else:
            # PERCENT
            tax = (base_amount * self.rate / Decimal("100")).quantize(
                Decimal(10) ** -decimal_places,
                rounding=ROUND_HALF_UP,
            )
            return tax

    def calculate_pretax_from_inclusive(
        self,
        inclusive_amount: Decimal,
        fraction: int = 100,
    ) -> Decimal:
        """
        BR-TAX-002: Calculate pre-tax amount from tax-inclusive price.

        pretax = (aggregate - tvalue) / (1 + tpercent)

        For tax-inclusive prices, the tax is embedded in the amount.
        """
        decimal_places = len(str(fraction - 1))

        if self.rule_type == TaxRuleType.VALUE:
            return (inclusive_amount - self.rate).quantize(
                Decimal(10) ** -decimal_places,
                rounding=ROUND_HALF_UP,
            )
        else:
            # PERCENT: pretax = aggregate / (1 + rate/100)
            divisor = Decimal("1") + (self.rate / Decimal("100"))
            pretax = (inclusive_amount / divisor).quantize(
                Decimal(10) ** -decimal_places,
                rounding=ROUND_HALF_UP,
            )
            return pretax


class PaymentTerm(models.Model):
    """
    Versioned payment term.

    Defines when payment is due and any early payment discounts.

    Attributes:
        guid: UUID primary key
        name: Payment term name (e.g., "Net 30")
        due_days: Number of days until payment is due
        discount_days: Days within which early payment discount applies
        discount_percent: Early payment discount percentage
        effective_from: When this term becomes effective
        effective_to: When this term expires
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    due_days = models.IntegerField()
    discount_days = models.IntegerField(default=0)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="payment_terms",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        ordering = ["-effective_from"]

    def __str__(self) -> str:
        return self.name

    def calculate_due_date(self, invoice_date) -> "date":
        """Calculate the due date from the invoice date."""
        from datetime import timedelta
        return invoice_date + timedelta(days=self.due_days)

    def calculate_discount_date(self, invoice_date) -> Optional["date"]:
        """Calculate the early payment discount deadline."""
        if self.discount_days == 0:
            return None
        from datetime import timedelta
        return invoice_date + timedelta(days=self.discount_days)

    def calculate_discount(
        self,
        invoice_amount: Decimal,
    ) -> Decimal:
        """Calculate early payment discount amount."""
        if self.discount_percent == 0:
            return Decimal("0.00")
        return (invoice_amount * self.discount_percent / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
