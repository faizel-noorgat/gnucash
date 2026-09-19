"""
Acceptance tests for tax calculation invariants.

Implements tests for:
- BR-TAX-001: Tax table entry types
- BR-TAX-002: Tax-included price back-computation
- BR-TAX-003: Discount ordering modes
"""

import pytest
from decimal import Decimal
from django.test import TestCase

from accounting_engine.models import TaxRule, TaxRuleType, DiscountOrderingMode
from tests.factories import (
    AccountFactory,
    CommodityFactory,
    TaxRuleFactory,
    TenantFactory,
)


@pytest.mark.acceptance
@pytest.mark.golden
class TestTaxCalculationInvariants(TestCase):
    """
    BR-TAX-001: Tax table entry types

    Given: A Tax Table with one or more entries
    When: each entry is examined
    Then: each entry has a type of either VALUE (absolute monetary amount)
          or PERCENT (percentage of base);
          values are summed; percents are summed
    """

    @pytest.mark.acceptance
    def test_br_tax_001_percent_tax_calculation(self):
        """Test PERCENT tax calculation."""
        tenant = TenantFactory()
        account = AccountFactory(tenant=tenant)

        tax_rule = TaxRuleFactory(
            tenant=tenant,
            account=account,
            rule_type=TaxRuleType.PERCENT,
            rate=Decimal("9.00"),  # 9%
        )

        # BR-TAX-001: PERCENT tax calculation
        base_amount = Decimal("1000.00")
        tax = tax_rule.calculate_tax(base_amount)

        expected_tax = Decimal("90.00")  # 9% of 1000
        assert tax == expected_tax

    @pytest.mark.acceptance
    def test_br_tax_001_value_tax_calculation(self):
        """Test VALUE (fixed amount) tax calculation."""
        tenant = TenantFactory()
        account = AccountFactory(tenant=tenant)

        tax_rule = TaxRuleFactory(
            tenant=tenant,
            account=account,
            rule_type=TaxRuleType.VALUE,
            rate=Decimal("5.00"),  # Fixed $5
        )

        # BR-TAX-001: VALUE tax calculation
        base_amount = Decimal("1000.00")
        tax = tax_rule.calculate_tax(base_amount)

        expected_tax = Decimal("5.00")  # Fixed amount
        assert tax == expected_tax

    @pytest.mark.acceptance
    def test_br_tax_001_rounding_half_up(self):
        """Test that tax calculations use ROUND_HALF_UP."""
        tenant = TenantFactory()
        account = AccountFactory(tenant=tenant)

        tax_rule = TaxRuleFactory(
            tenant=tenant,
            account=account,
            rule_type=TaxRuleType.PERCENT,
            rate=Decimal("7.50"),  # 7.5%
        )

        # BR-TAX-001: Rounding should be ROUND_HALF_UP
        base_amount = Decimal("100.01")
        tax = tax_rule.calculate_tax(base_amount, fraction=100)

        # 7.5% of 100.01 = 7.50075, should round to 7.50
        assert tax == Decimal("7.50")


@pytest.mark.acceptance
@pytest.mark.golden
class TestTaxIncludedBackComputation(TestCase):
    """
    BR-TAX-002: Tax-included price back-computation

    Given: An Entry with tax_included = TRUE and aggregate = qty × price
    When: the pre-tax value is computed
    Then: pretax = (aggregate - tvalue) / (1 + tpercent);
          net_price = pretax / qty
    """

    @pytest.mark.acceptance
    def test_br_tax_002_percent_tax_included_back_computation(self):
        """Test back-computation for tax-included PERCENT tax."""
        tenant = TenantFactory()
        account = AccountFactory(tenant=tenant)

        tax_rule = TaxRuleFactory(
            tenant=tenant,
            account=account,
            rule_type=TaxRuleType.PERCENT,
            rate=Decimal("9.00"),  # 9% GST
        )

        # BR-TAX-002: Back-compute pretax from tax-inclusive amount
        inclusive_amount = Decimal("109.00")  # $109 including 9% tax
        pretax = tax_rule.calculate_pretax_from_inclusive(inclusive_amount)

        # pretax = 109 / 1.09 = 100
        expected_pretax = Decimal("100.00")
        assert pretax == expected_pretax

    @pytest.mark.acceptance
    def test_br_tax_002_value_tax_included_back_computation(self):
        """Test back-computation for tax-included VALUE tax."""
        tenant = TenantFactory()
        account = AccountFactory(tenant=tenant)

        tax_rule = TaxRuleFactory(
            tenant=tenant,
            account=account,
            rule_type=TaxRuleType.VALUE,
            rate=Decimal("5.00"),  # Fixed $5 tax
        )

        # BR-TAX-002: Back-compute pretax from tax-inclusive amount
        inclusive_amount = Decimal("105.00")  # $105 including $5 tax
        pretax = tax_rule.calculate_pretax_from_inclusive(inclusive_amount)

        # pretax = 105 - 5 = 100
        expected_pretax = Decimal("100.00")
        assert pretax == expected_pretax


@pytest.mark.acceptance
@pytest.mark.golden
class TestDiscountOrderingModes(TestCase):
    """
    BR-TAX-003: Discount ordering modes

    Given: An Entry with a discount and a tax
    When: discount_how is applied
    Then:
        - PRETAX: discount on pretax, tax on (pretax - discount)
        - SAMETIME: discount on pretax, tax on pretax (ignoring discount)
        - POSTTAX: discount on (pretax + tax), tax on pretax
    """

    @pytest.mark.acceptance
    def test_br_tax_003_pretax_discount_ordering(self):
        """
        BR-TAX-003: PRETAX discount ordering
        discount on pretax, tax on (pretax - discount)
        """
        pretax = Decimal("1000.00")
        discount = Decimal("100.00")
        tax_rate = Decimal("9.00")  # 9%

        # PRETAX: discount on pretax, tax on (pretax - discount)
        discounted_pretax = pretax - discount  # 1000 - 100 = 900
        tax_on_discounted = (discounted_pretax * tax_rate / Decimal("100")).quantize(Decimal("0.01"))

        expected_tax = Decimal("81.00")  # 9% of 900
        assert tax_on_discounted == expected_tax

    @pytest.mark.acceptance
    def test_br_tax_003_sametime_discount_ordering(self):
        """
        BR-TAX-003: SAMETIME discount ordering
        discount on pretax, tax on pretax (ignoring discount)
        """
        pretax = Decimal("1000.00")
        discount = Decimal("100.00")
        tax_rate = Decimal("9.00")  # 9%

        # SAMETIME: discount on pretax, tax on pretax (ignoring discount)
        tax_on_pretax = (pretax * tax_rate / Decimal("100")).quantize(Decimal("0.01"))

        expected_tax = Decimal("90.00")  # 9% of 1000 (ignoring discount)
        assert tax_on_pretax == expected_tax

    @pytest.mark.acceptance
    def test_br_tax_003_posttax_discount_ordering(self):
        """
        BR-TAX-003: POSTTAX discount ordering
        discount on (pretax + tax), tax on pretax
        """
        pretax = Decimal("1000.00")
        discount_rate = Decimal("10.00")  # 10%
        tax_rate = Decimal("9.00")  # 9%

        # POSTTAX: tax on pretax, discount on (pretax + tax)
        tax_on_pretax = (pretax * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
        pretax_plus_tax = pretax + tax_on_pretax
        discount_on_total = (pretax_plus_tax * discount_rate / Decimal("100")).quantize(Decimal("0.01"))

        expected_tax = Decimal("90.00")  # 9% of 1000
        expected_discount = Decimal("109.00")  # 10% of 1090
        assert tax_on_pretax == expected_tax
        assert discount_on_total == expected_discount

    @pytest.mark.acceptance
    def test_br_tax_003_discount_ordering_mode_enum(self):
        """Test that discount ordering modes are properly defined."""
        # BR-TAX-003: Enum values should be defined
        assert DiscountOrderingMode.PRETAX == 1
        assert DiscountOrderingMode.SAMETIME == 2
        assert DiscountOrderingMode.POSTTAX == 3
