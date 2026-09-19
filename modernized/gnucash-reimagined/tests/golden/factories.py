"""
Test factories for accounting engine.

Uses factory-boy for test data generation.
"""

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

User = get_user_model()


class TenantFactory(DjangoModelFactory):
    """Factory for Tenant model (from identity app)."""

    class Meta:
        # This would be in the identity app, but we need it for tests
        model = "identity.Tenant"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    name = factory.Sequence(lambda n: f"Test Tenant {n}")
    slug = factory.Sequence(lambda n: f"test-tenant-{n}")


class LegalEntityFactory(DjangoModelFactory):
    """Factory for LegalEntity model (from identity app)."""

    class Meta:
        model = "identity.LegalEntity"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    name = factory.Sequence(lambda n: f"Test Entity {n}")
    tenant = factory.SubFactory(TenantFactory)


class UserFactory(DjangoModelFactory):
    """Factory for User model."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class CommodityFactory(DjangoModelFactory):
    """Factory for Commodity model."""

    class Meta:
        model = "accounting_engine.Commodity"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    namespace = "CURRENCY"
    mnemonic = factory.Sequence(lambda n: f"CUR{n}")
    fullname = factory.LazyAttribute(lambda obj: f"Currency {obj.mnemonic}")
    fraction = 100
    tenant = factory.SubFactory(TenantFactory)


class CurrencyFactory(CommodityFactory):
    """Factory for Currency (proxy)."""

    namespace = "CURRENCY"


class AccountFactory(DjangoModelFactory):
    """Factory for Account model."""

    class Meta:
        model = "accounting_engine.Account"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    name = factory.Sequence(lambda n: f"Test Account {n}")
    code = factory.Sequence(lambda n: f"ACC{n:04d}")
    account_type = "ASSET"
    commodity = factory.SubFactory(CommodityFactory)
    tenant = factory.SubFactory(TenantFactory)
    legal_entity = factory.SubFactory(LegalEntityFactory)


class JournalEntryFactory(DjangoModelFactory):
    """Factory for JournalEntry model."""

    class Meta:
        model = "accounting_engine.JournalEntry"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    date = factory.LazyFunction(lambda: __import__("datetime").date.today())
    description = factory.Sequence(lambda n: f"Test Journal Entry {n}")
    transaction_currency = factory.SubFactory(CommodityFactory)
    tenant = factory.SubFactory(TenantFactory)
    legal_entity = factory.SubFactory(LegalEntityFactory)


class JournalLineFactory(DjangoModelFactory):
    """Factory for JournalLine model."""

    class Meta:
        model = "accounting_engine.JournalLine"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    journal_entry = factory.SubFactory(JournalEntryFactory)
    account = factory.SubFactory(AccountFactory)
    amount = 100.00
    value = 100.00


class FiscalPeriodFactory(DjangoModelFactory):
    """Factory for FiscalPeriod model."""

    class Meta:
        model = "accounting_engine.FiscalPeriod"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    name = factory.Sequence(lambda n: f"Period {n}")
    start_date = factory.LazyFunction(lambda: __import__("datetime").date.today().replace(month=1, day=1))
    end_date = factory.LazyFunction(lambda: __import__("datetime").date.today().replace(month=12, day=31))
    status = "open"
    fiscal_year = factory.LazyFunction(lambda: __import__("datetime").date.today().year)
    tenant = factory.SubFactory(TenantFactory)
    legal_entity = factory.SubFactory(LegalEntityFactory)


class TaxRuleFactory(DjangoModelFactory):
    """Factory for TaxRule model."""

    class Meta:
        model = "accounting_engine.TaxRule"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    name = factory.Sequence(lambda n: f"Tax Rule {n}")
    code = factory.Sequence(lambda n: f"TAX{n}")
    rule_type = "PERCENT"
    rate = 9.00
    effective_from = factory.LazyFunction(lambda: __import__("datetime").date.today())
    account = factory.SubFactory(AccountFactory)
    tenant = factory.SubFactory(TenantFactory)


class PaymentTermFactory(DjangoModelFactory):
    """Factory for PaymentTerm model."""

    class Meta:
        model = "accounting_engine.PaymentTerm"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    name = factory.Sequence(lambda n: f"Payment Term {n}")
    due_days = 30
    discount_days = 10
    discount_percent = 2.00
    effective_from = factory.LazyFunction(lambda: __import__("datetime").date.today())
    tenant = factory.SubFactory(TenantFactory)


class LotFactory(DjangoModelFactory):
    """Factory for Lot model."""

    class Meta:
        model = "accounting_engine.Lot"

    guid = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    title = factory.Sequence(lambda n: f"Test Lot {n}")
    account = factory.SubFactory(AccountFactory)
    tenant = factory.SubFactory(TenantFactory)
    legal_entity = factory.SubFactory(LegalEntityFactory)
