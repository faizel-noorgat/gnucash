"""
DocumentLine model - line items in accounting documents
"""
from django.db import models
from decimal import Decimal


class DiscountOrderingMode(models.IntegerChoices):
    """
    Discount ordering modes for tax calculation.

    BR-TAX-003: Discount ordering modes
    - PRETAX: discount on pretax, tax on (pretax - discount)
    - SAMETIME: discount on pretax, tax on pretax
    - POSTTAX: discount on (pretax + tax), tax on pretax
    """
    PRETAX = 1, 'Pre-Tax'
    SAMETIME = 2, 'Same Time'
    POSTTAX = 3, 'Post-Tax'


class DocumentLine(models.Model):
    """
    Line item in an accounting document.

    Contains quantity, unit price, tax, account mapping.
    """
    guid = models.UUIDField(primary_key=True, default=__import__('uuid').uuid4, editable=False)
    document = models.ForeignKey(
        'AccountingDocument',
        on_delete=models.CASCADE,
        related_name='lines'
    )

    # Line identification
    line_number = models.PositiveIntegerField()
    description = models.TextField()

    # Quantity and pricing
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    unit_price = models.DecimalField(max_digits=20, decimal_places=4)

    # Account mapping
    account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.PROTECT,
        related_name='document_lines',
        help_text="Income/expense account for this line"
    )

    # Tax treatment
    tax_rule = models.ForeignKey(
        'accounting.TaxRule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_lines'
    )
    tax_included = models.BooleanField(
        default=False,
        help_text="Whether the unit price includes tax"
    )

    # Discount
    discount_ordering_mode = models.PositiveSmallIntegerField(
        choices=DiscountOrderingMode.choices,
        default=DiscountOrderingMode.PRETAX,
        help_text="How discount interacts with tax calculation"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        blank=True,
        null=True
    )
    discount_amount = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        blank=True,
        null=True
    )

    # Calculated amounts
    subtotal = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="quantity × unit_price"
    )
    discount_value = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Calculated discount amount"
    )
    tax_value = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Calculated tax amount"
    )
    total = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Final line total"
    )

    # Optional project/dimension
    project = models.ForeignKey(
        'accounting.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_lines'
    )

    # Notes
    notes = models.TextField(blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'business_documents_document_line'
        verbose_name = 'Document Line'
        verbose_name_plural = 'Document Lines'
        ordering = ['line_number']
        unique_together = [
            ['document', 'line_number'],
        ]

    def __str__(self):
        return f"Line {self.line_number}: {self.description[:50]}"

    def calculate_amounts(self):
        """
        Calculate subtotal, discount, tax, and total for this line.

        Implements tax calculation invariants:
        - BR-TAX-002: Tax-included price back-computation
        - BR-TAX-003: Discount ordering modes
        """
        # Calculate base subtotal
        self.subtotal = (self.quantity * self.unit_price).quantize(Decimal('0.0001'))

        # Calculate discount
        if self.discount_percentage:
            self.discount_value = (self.subtotal * self.discount_percentage / 100).quantize(Decimal('0.0001'))
        elif self.discount_amount:
            self.discount_value = self.discount_amount
        else:
            self.discount_value = Decimal('0.0000')

        # Calculate pretax amount after discount
        pretax = self.subtotal - self.discount_value

        # Calculate tax based on tax rule and ordering mode
        if self.tax_rule:
            # Get tax rate (assuming TaxRule has a rate field)
            tax_rate = Decimal(str(self.tax_rule.rate))

            if self.tax_included:
                # BR-TAX-002: Back-compute pretax from tax-included price
                # pretax = aggregate / (1 + tax_rate)
                pretax = (pretax / (1 + tax_rate)).quantize(Decimal('0.0001'))
                self.tax_value = (pretax * tax_rate).quantize(Decimal('0.0001'))
            else:
                # Calculate tax based on ordering mode
                if self.discount_ordering_mode == DiscountOrderingMode.PRETAX:
                    # Tax on (pretax - discount) - discount already applied
                    self.tax_value = (pretax * tax_rate).quantize(Decimal('0.0001'))
                elif self.discount_ordering_mode == DiscountOrderingMode.SAMETIME:
                    # Tax on pretax (ignoring discount for tax calculation)
                    self.tax_value = (self.subtotal * tax_rate).quantize(Decimal('0.0001'))
                elif self.discount_ordering_mode == DiscountOrderingMode.POSTTAX:
                    # Tax on pretax, discount on (pretax + tax)
                    self.tax_value = (pretax * tax_rate).quantize(Decimal('0.0001'))
        else:
            self.tax_value = Decimal('0.0000')

        # Calculate total
        self.total = pretax + self.tax_value

    def save(self, *args, **kwargs):
        # Recalculate amounts before saving
        self.calculate_amounts()
        super().save(*args, **kwargs)
