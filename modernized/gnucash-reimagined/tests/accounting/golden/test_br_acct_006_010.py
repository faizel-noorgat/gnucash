"""
Acceptance tests for account type invariants.

Implements tests for:
- BR-ACCT-006: Account fundamental types
- BR-ACCT-007: AP/AR type detection
- BR-ACCT-010: Root account cannot have parent
"""

import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.accounting.models import Account, AccountType, FundamentalType
from tests.accounting.golden.factories import (
    AccountFactory,
    CommodityFactory,
    TenantFactory,
    LegalEntityFactory,
)


@pytest.mark.acceptance
@pytest.mark.golden
class TestAccountTypeInvariants(TestCase):
    """
    BR-ACCT-006: Account fundamental types

    Given: A GNCAccountType value
    When: fundamental type is determined
    Then: BANK/STOCK/MONEYMRKT/CHECKING/SAVINGS/MUTUAL/CURRENCY/CASH/ASSET/RECEIVABLE → ASSET;
          CREDIT/LIABILITY/PAYABLE/CREDITLINE → LIABILITY;
          INCOME → INCOME;
          EXPENSE → EXPENSE;
          EQUITY → EQUITY
    """

    @pytest.mark.acceptance
    def test_br_acct_006_asset_types(self):
        """Test that asset account types map to ASSET fundamental type."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        asset_types = [
            AccountType.BANK,
            AccountType.CASH,
            AccountType.ASSET,
            AccountType.RECEIVABLE,
            AccountType.STOCK,
            AccountType.MUTUAL,
            AccountType.CURRENCY,
            AccountType.CHECKING,
            AccountType.SAVINGS,
            AccountType.MONEYMRKT,
        ]

        for account_type in asset_types:
            account = AccountFactory(
                tenant=tenant,
                legal_entity=legal_entity,
                commodity=currency,
                account_type=account_type,
            )
            # BR-ACCT-006: These should all map to ASSET
            assert account.fundamental_type == FundamentalType.ASSET, \
                f"Account type {account_type} should map to ASSET"

    @pytest.mark.acceptance
    def test_br_acct_006_liability_types(self):
        """Test that liability account types map to LIABILITY fundamental type."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        liability_types = [
            AccountType.CREDIT,
            AccountType.LIABILITY,
            AccountType.PAYABLE,
            AccountType.CREDITLINE,
        ]

        for account_type in liability_types:
            account = AccountFactory(
                tenant=tenant,
                legal_entity=legal_entity,
                commodity=currency,
                account_type=account_type,
            )
            # BR-ACCT-006: These should all map to LIABILITY
            assert account.fundamental_type == FundamentalType.LIABILITY, \
                f"Account type {account_type} should map to LIABILITY"

    @pytest.mark.acceptance
    def test_br_acct_006_income_expense_equity_types(self):
        """Test that INCOME/EXPENSE/EQUITY types map correctly."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        # INCOME
        income_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type=AccountType.INCOME,
        )
        assert income_account.fundamental_type == FundamentalType.INCOME

        # EXPENSE
        expense_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type=AccountType.EXPENSE,
        )
        assert expense_account.fundamental_type == FundamentalType.EXPENSE

        # EQUITY
        equity_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type=AccountType.EQUITY,
        )
        assert equity_account.fundamental_type == FundamentalType.EQUITY


@pytest.mark.acceptance
@pytest.mark.golden
class TestAPARDetection(TestCase):
    """
    BR-ACCT-007: AP/AR type detection

    Given: A GNCAccountType value
    When: AP/AR type check is performed
    Then: returns TRUE only for RECEIVABLE or PAYABLE;
          all other types return FALSE
    """

    @pytest.mark.acceptance
    def test_br_acct_007_receivable_is_ap_ar(self):
        """Test that RECEIVABLE accounts are detected as AP/AR."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type=AccountType.RECEIVABLE,
        )

        # BR-ACCT-007: RECEIVABLE should be detected as AP/AR
        assert account.is_ap_ar is True

    @pytest.mark.acceptance
    def test_br_acct_007_payable_is_ap_ar(self):
        """Test that PAYABLE accounts are detected as AP/AR."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type=AccountType.PAYABLE,
        )

        # BR-ACCT-007: PAYABLE should be detected as AP/AR
        assert account.is_ap_ar is True

    @pytest.mark.acceptance
    def test_br_acct_007_other_types_not_ap_ar(self):
        """Test that other account types are NOT detected as AP/AR."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        non_ap_ar_types = [
            AccountType.BANK,
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.INCOME,
            AccountType.EXPENSE,
            AccountType.EQUITY,
        ]

        for account_type in non_ap_ar_types:
            account = AccountFactory(
                tenant=tenant,
                legal_entity=legal_entity,
                commodity=currency,
                account_type=account_type,
            )
            # BR-ACCT-007: These should NOT be AP/AR
            assert account.is_ap_ar is False, \
                f"Account type {account_type} should NOT be AP/AR"


@pytest.mark.acceptance
@pytest.mark.golden
class TestRootAccountInvariants(TestCase):
    """
    BR-ACCT-010: Root account cannot have parent

    Given: An account of type ROOT
    When: parent account compatibility is checked
    Then: returns FALSE — root accounts cannot have parent accounts
    """

    @pytest.mark.acceptance
    def test_br_acct_010_root_cannot_have_parent(self):
        """Test that root accounts cannot have a parent."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        parent_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type=AccountType.ASSET,
        )

        root_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type=AccountType.ROOT,
            parent=None,
        )

        # BR-ACCT-010: Root account cannot have parent. The invalid state is
        # constructed by the attempted update, not by the initial fixture.
        root_account.parent = parent_account
        with pytest.raises(ValidationError, match="Root account cannot have a parent"):
            root_account.save()

    @pytest.mark.acceptance
    def test_br_acct_010_root_without_parent_is_valid(self):
        """Test that root accounts without parent are valid."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        root_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type=AccountType.ROOT,
            parent=None,
        )

        # BR-ACCT-010: Root without parent should be valid
        root_account.full_clean()  # Should not raise
