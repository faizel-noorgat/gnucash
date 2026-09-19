"""
Acceptance tests for foreign exchange invariants.

Implements tests for:
- BR-FX-001: Price lookup nearest-in-time
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase

from apps.accounting.models import ExchangeRate, Commodity
from tests.accounting.golden.factories import (
    CommodityFactory,
    TenantFactory,
)


@pytest.mark.acceptance
@pytest.mark.golden
class TestForeignExchangeInvariants(TestCase):
    """
    BR-FX-001: Price lookup nearest-in-time

    Given: A PriceDB and a (commodity, currency, time) tuple
    When: nearest-in-time lookup is called
    Then: returns the price closest to time t (can be before or after)
    """

    @pytest.mark.acceptance
    def test_br_fx_001_exact_date_match(self):
        """Test that exact date match returns the correct rate."""
        tenant = TenantFactory()
        usd = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)
        sgd = CommodityFactory(tenant=tenant, mnemonic="SGD", fraction=100)

        target_date = date(2026, 1, 15)

        # Create exchange rate
        ExchangeRate.objects.create(
            from_commodity=usd,
            to_commodity=sgd,
            rate_date=target_date,
            rate=Decimal("1.3400"),
            source="manual",
            tenant=tenant,
        )

        # BR-FX-001: Exact date match
        rate = ExchangeRate.get_rate(usd, sgd, target_date, tenant)
        assert rate is not None
        assert rate.rate == Decimal("1.3400")

    @pytest.mark.acceptance
    def test_br_fx_001_most_recent_rate_before(self):
        """Test that most recent rate before the date is returned."""
        tenant = TenantFactory()
        usd = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)
        sgd = CommodityFactory(tenant=tenant, mnemonic="SGD", fraction=100)

        target_date = date(2026, 1, 15)
        earlier_date = date(2026, 1, 10)

        # Create exchange rate for earlier date
        ExchangeRate.objects.create(
            from_commodity=usd,
            to_commodity=sgd,
            rate_date=earlier_date,
            rate=Decimal("1.3350"),
            source="manual",
            tenant=tenant,
        )

        # BR-FX-001: Should return most recent rate before target date
        rate = ExchangeRate.get_rate(usd, sgd, target_date, tenant)
        assert rate is not None
        assert rate.rate == Decimal("1.3350")

    @pytest.mark.acceptance
    def test_br_fx_001_same_commodity_returns_none(self):
        """Test that same commodity returns None (1:1 rate)."""
        tenant = TenantFactory()
        usd = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        target_date = date(2026, 1, 15)

        # BR-FX-001: Same commodity should return None
        rate = ExchangeRate.get_rate(usd, usd, target_date, tenant)
        assert rate is None

    @pytest.mark.acceptance
    def test_br_fx_001_no_rate_found(self):
        """Test that None is returned when no rate is found."""
        tenant = TenantFactory()
        usd = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)
        sgd = CommodityFactory(tenant=tenant, mnemonic="SGD", fraction=100)

        target_date = date(2026, 1, 15)

        # BR-FX-001: No rate found should return None
        rate = ExchangeRate.get_rate(usd, sgd, target_date, tenant)
        assert rate is None
