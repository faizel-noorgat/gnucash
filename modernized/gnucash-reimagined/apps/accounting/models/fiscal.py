"""
Fiscal period, tax, and payment term models.

Implements:
- Period locking to prevent posting to closed periods
- BR-TAX-001: Tax table entry types (VALUE, PERCENT)
- BR-TAX-002: Tax-included price back-computation
- BR-TAX-003: Discount ordering modes (PRETAX, SAMETIME, POSTTAX)
- Versioned tax rules with effective dates
- frozen_tax_table_json snapshot at posting (ADR-010)

Accounting Semantics:
    Fiscal periods are used for period-end controls and financial reporting.
    Tax rules define how taxes are calculated on transactions.
    Payment terms define when payment is due and any early payment discounts.

    Period locking ensures that financial reports remain stable after closing.
    Once a period is locked, no new transactions can be posted to it.

    Tax rules are versioned with effective dates, allowing historical tax rates
    to be preserved for audit purposes.
"""

import uuid
from datetime import date
from typing import Optional

from django.db import models


class FiscalPeriodStatus(models.TextChoices):
    """
    Fiscal period status.

    Accounting Semantics:
        OPEN: Posting is allowed
        CLOSED: Posting is prevented, but can be reopened
        LOCKED: Posting is prevented permanently (cannot be reopened)
    """

    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    LOCKED = "locked", "Locked"


class FiscalPeriod(models.Model):
    """
    Fiscal period for period-end controls.

    Accounting Semantics:
        Fiscal periods define the boundaries for financial reporting.
        Transactions are posted to specific periods based on their date.
        Periods can be closed to prevent further posting, ensuring report stability.

        Period Lifecycle:
        1. OPEN: Transactions can be posted
        2. CLOSED: Posting prevented, but can be reopened if needed
        3. LOCKED: Posting prevented permanently (cannot be reopened)

        Period-End Process:
        1. Review all transactions in the period
        2. Make adjusting entries if needed
        3. Close the period (prevents further posting)
        4. Generate financial reports
        5. Lock the period (optional, makes it permanent)

    Attributes:
        guid: UUID primary key
        name: Period name (e.g., "Q1 2024", "January 2024")
        start_date: Period start date (inclusive)
        end_date: Period end date (inclusive)
        status: OPEN, CLOSED, or LOCKED
        fiscal_year: Fiscal year (e.g., 2024)
        tenant: Multi-tenant isolation
        legal_entity: Legal entity that owns this period
        closed_at: When the period was closed
        closed_by: User who closed the period
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
        app_label = "accounting"
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
        """
        Check if period is open for posting.

        Returns:
            True if status is OPEN, False otherwise
        """
        return self.status == FiscalPeriodStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """
        Check if period is closed.

        Returns:
            True if status is CLOSED, False otherwise
        """
        return self.status == FiscalPeriodStatus.CLOSED

    @property
    def is_locked(self) -> bool:
        """
        Check if period is locked (cannot be reopened).

        Returns:
            True if status is LOCKED, False otherwise
        """
        return self.status == FiscalPeriodStatus.LOCKED

    def close(self, user=None):
        """
        Close the fiscal period.

        Accounting Semantics:
            Closing a period prevents further posting.
            This is done at period-end after all adjustments are made.
            A closed period can be reopened if needed (unlike LOCKED).

        Args:
            user: User closing the period

        Raises:
            ValueError: If period is not OPEN
        """
        if self.status != FiscalPeriodStatus.OPEN:
            raise ValueError("Can only close open periods.")

        from django.utils import timezone

        self.status = FiscalPeriodStatus.CLOSED
        self.closed_at = timezone.now()
        self.closed_by = user
        self.save()

    def lock(self, user=None):
        """
        Lock the fiscal period (permanent).

        Accounting Semantics:
            Locking a period makes it permanently closed.
            A locked period cannot be reopened.
            This is typically done after generating final financial reports.

        Args:
            user: User locking the period
        """
        self.status = FiscalPeriodStatus.LOCKED
        self.closed_at = self.closed_at or timezone.now()
        self.closed_by = user
        self.save()

    def reopen(self):
        """
        Reopen a closed period (only if not locked).

        Accounting Semantics:
            Reopening allows posting to a previously closed period.
            This is used when adjustments are needed after closing.
            Locked periods cannot be reopened.

        Raises:
            ValueError: If period is LOCKED
        """
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
        """
        Get the fiscal period for a given date.

        Accounting Semantics:
            This is used during journal posting to determine which period
            the transaction belongs to. If no period is found, the transaction
            can still be posted (no period control). If a period is found
            but it's not OPEN, posting is prevented.

        Args:
            tenant: Multi-tenant isolation
            legal_entity: Legal entity context
            transaction_date: Date of the transaction

        Returns:
            FiscalPeriod instance or None if no period covers this date
        """
        return cls.objects.filter(
            tenant=tenant,
            legal_entity=legal_entity,
            start_date__lte=transaction_date,
            end_date__gte=transaction_date,
        ).first()


# ============================================================================
# Tax and Payment Term Models
# ============================================================================

class TaxRuleType(models.TextChoices):
    """
    Tax calculation type.

    Accounting Semantics:
        VALUE: Fixed amount tax (e.g., $2.00 per transaction)
        PERCENT: Percentage tax (e.g., 9% GST)
    """

    VALUE = "VALUE", "Absolute Amount"
    PERCENT = "PERCENT", "Percentage"


class DiscountOrderingMode(models.IntegerChoices):
    """
    BR-TAX-003: Discount ordering modes.

    Accounting Semantics:
        The ordering mode determines how discounts and taxes are applied:

        - PRETAX (1): discount on pretax, tax on (pretax - discount)
          Example: $100 item, 10% discount, 9% tax
          → Discount: $10, Taxable: $90, Tax: $8.10, Total: $88.10

        - SAMETIME (2): discount on pretax, tax on pretax (ignoring discount)
          Example: $100 item, 10% discount, 9% tax
          → Discount: $10, Taxable: $100, Tax: $9.00, Total: $99.00

        - POSTTAX (3): discount on (pretax + tax), tax on pretax
          Example: $100 item, 10% discount, 9% tax
          → Taxable: $100, Tax: $9.00, Subtotal: $109, Discount: $10.90, Total: $98.10
    """

    PRETAX = 1, "Pre-Tax"
    SAMETIME = 2, "Same Time"
    POSTTAX = 3, "Post-Tax"


class TaxRule(models.Model):
    """
    Versioned tax rule with effective dates.

    Accounting Semantics:
        Tax rules define how taxes are calculated on transactions.
        Rules are versioned with effective dates, allowing historical tax rates
        to be preserved for audit purposes.

        When a transaction is posted, the applicable tax rate is determined
        based on the transaction date and frozen in the journal entry metadata
        (ADR-010: frozen_tax_table_json).

        Tax Calculation (BR-TAX-001):
        - VALUE: Fixed amount (e.g., $2.00 per transaction)
        - PERCENT: Percentage of base amount (e.g., 9% GST)

        Tax-Included Prices (BR-TAX-002):
        When tax is included in the price, the pre-tax amount is calculated as:
        pretax = (aggregate - tvalue) / (1 + tpercent)

    Attributes:
        guid: UUID primary key
        name: Tax rule name (e.g., "GST 9%", "State Tax")
        code: Tax code (e.g., "GST", "STATE_TAX")
        rule_type: VALUE or PERCENT
        rate: Tax rate (for PERCENT) or fixed amount (for VALUE)
        effective_from: When this rule becomes effective
        effective_to: When this rule expires (null = still active)
        account: Tax account for posting (liability account)
        is_active: Whether this rule is currently active
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
        "accounting.Account",
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
        app_label = "accounting"
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
        """
        Get the applicable tax rule for a given date.

        Accounting Semantics:
            This method finds the tax rule that was in effect on the transaction date.
            It considers:
            - The tax code (e.g., "GST", "STATE_TAX")
            - The effective date range (effective_from <= date <= effective_to)
            - Whether the rule is active
            - If multiple rules match, the most recent one is returned

        Args:
            tenant: Multi-tenant isolation
            tax_code: Tax code to look up
            transaction_date: Date of the transaction

        Returns:
            TaxRule instance or None if no rule applies
        """
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

        Accounting Semantics:
            BR-TAX-001: Tax table entry types
            - VALUE: Fixed amount (e.g., $2.00 per transaction)
            - PERCENT: Percentage of base amount (e.g., 9% GST)

            BR-TAX-002: Tax-included price back-computation
            If tax is included in the price:
            pretax = (aggregate - tvalue) / (1 + tpercent)

        Args:
            base_amount: Base amount to calculate tax on
            fraction: Commodity fraction (e.g., 100 for 2 decimal places)

        Returns:
            Decimal tax amount, rounded to commodity precision
        """
        from decimal import ROUND_HALF_UP
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

        Accounting Semantics:
            When tax is included in the price, the pre-tax amount is calculated as:
            pretax = (aggregate - tvalue) / (1 + tpercent)

            Example:
            - Inclusive amount: $109 (includes 9% GST)
            - Pre-tax amount: $100
            - Tax: $9

        Args:
            inclusive_amount: Amount including tax
            fraction: Commodity fraction (e.g., 100 for 2 decimal places)

        Returns:
            Decimal pre-tax amount, rounded to commodity precision
        """
        from decimal import ROUND_HALF_UP
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

    Accounting Semantics:
        Payment terms define when payment is due and any early payment discounts.

        Common payment terms:
        - Net 30: Payment due in 30 days
        - 2/10 Net 30: 2% discount if paid within 10 days, otherwise due in 30 days
        - Due on receipt: Payment due immediately

        The payment term is applied to invoices to calculate:
        - Due date (invoice_date + due_days)
        - Discount deadline (invoice_date + discount_days)
        - Discount amount (invoice_amount * discount_percent / 100)

    Attributes:
        guid: UUID primary key
        name: Payment term name (e.g., "Net 30", "2/10 Net 30")
        due_days: Number of days until payment is due
        discount_days: Days within which early payment discount applies
        discount_percent: Early payment discount percentage (e.g., 2.00 for 2%)
        effective_from: When this term becomes effective
        effective_to: When this term expires
        is_active: Whether this term is currently active
        tenant: Multi-tenant isolation
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
        app_label = "accounting"
        ordering = ["-effective_from"]

    def __str__(self) -> str:
        return self.name

    def calculate_due_date(self, invoice_date) -> "date":
        """
        Calculate the due date from the invoice date.

        Args:
            invoice_date: Date of the invoice

        Returns:
            date when payment is due
        """
        from datetime import timedelta
        return invoice_date + timedelta(days=self.due_days)

    def calculate_discount_date(self, invoice_date) -> Optional["date"]:
        """
        Calculate the early payment discount deadline.

        Args:
            invoice_date: Date of the invoice

        Returns:
            date when discount expires, or None if no discount
        """
        if self.discount_days == 0:
            return None
        from datetime import timedelta
        return invoice_date + timedelta(days=self.discount_days)

    def calculate_discount(
        self,
        invoice_amount: Decimal,
    ) -> Decimal:
        """
        Calculate early payment discount amount.

        Args:
            invoice_amount: Invoice amount

        Returns:
            Decimal discount amount (0 if no discount)
        """
        from decimal import ROUND_HALF_UP
        if self.discount_percent == 0:
            return Decimal("0.00")
        return (invoice_amount * self.discount_percent / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
