"""
API serializers for accounting app.

This module contains Django REST Framework serializer classes for all accounting models.

Serializer Classes:
    - CommoditySerializer, CurrencySerializer, ExchangeRateSerializer
    - AccountSerializer
    - JournalEntrySerializer, JournalLineSerializer
    - LotSerializer
    - FiscalPeriodSerializer, TaxRuleSerializer, PaymentTermSerializer
    - BankAccountSerializer, BankStatementSerializer, BankTransactionSerializer
    - BankReconciliationSerializer
    - IntercompanyRelationshipSerializer, InterEntityEventSerializer
    - AuditEventSerializer

Note:
    This is a stub implementation. Full serializer implementations will be added later.
"""

from rest_framework import serializers


class CommoditySerializer(serializers.Serializer):
    """Serializer for Commodity model."""

    guid = serializers.UUIDField(read_only=True)
    namespace = serializers.ChoiceField(choices=["CURRENCY", "SECURITY", "CRYPTO"])
    mnemonic = serializers.CharField(max_length=10)
    fullname = serializers.CharField(max_length=255)
    fraction = serializers.IntegerField(default=100)
    tenant = serializers.UUIDField()

    # Stub - will be fully implemented later
    pass


class CurrencySerializer(CommoditySerializer):
    """Serializer for Currency model (proxy)."""

    pass


class ExchangeRateSerializer(serializers.Serializer):
    """Serializer for ExchangeRate model."""

    guid = serializers.UUIDField(read_only=True)
    from_commodity = serializers.UUIDField()
    to_commodity = serializers.UUIDField()
    rate_date = serializers.DateField()
    rate = serializers.DecimalField(max_digits=20, decimal_places=10)
    source = serializers.CharField(max_length=50)

    # Stub - will be fully implemented later
    pass


class AccountSerializer(serializers.Serializer):
    """Serializer for Account model."""

    guid = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=50, required=False)
    account_type = serializers.ChoiceField(choices=[
        "BANK", "CASH", "CREDIT", "ASSET", "RECEIVABLE", "STOCK", "MUTUAL",
        "CURRENCY", "CHECKING", "SAVINGS", "MONEYMRKT", "LIABILITY", "PAYABLE",
        "CREDITLINE", "INCOME", "EXPENSE", "EQUITY", "ROOT", "TRADING",
    ])
    commodity = serializers.UUIDField()
    parent = serializers.UUIDField(required=False, allow_null=True)
    is_placeholder = serializers.BooleanField(default=False)
    is_system_account = serializers.BooleanField(default=False)

    # Stub - will be fully implemented later
    pass


class JournalEntrySerializer(serializers.Serializer):
    """Serializer for JournalEntry model."""

    guid = serializers.UUIDField(read_only=True)
    date = serializers.DateField()
    description = serializers.CharField(max_length=1024)
    transaction_currency = serializers.UUIDField()
    status = serializers.ChoiceField(choices=["draft", "posted", "reversed", "void"])
    is_posted = serializers.BooleanField(read_only=True)

    # Stub - will be fully implemented later
    pass


class JournalLineSerializer(serializers.Serializer):
    """Serializer for JournalLine model."""

    guid = serializers.UUIDField(read_only=True)
    journal_entry = serializers.UUIDField()
    account = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=20, decimal_places=10)
    value = serializers.DecimalField(max_digits=20, decimal_places=10)
    memo = serializers.CharField(max_length=1024, required=False)

    # Stub - will be fully implemented later
    pass


class LotSerializer(serializers.Serializer):
    """Serializer for Lot model."""

    guid = serializers.UUIDField(read_only=True)
    title = serializers.CharField(max_length=255)
    account = serializers.UUIDField()
    is_closed = serializers.BooleanField(read_only=True)

    # Stub - will be fully implemented later
    pass


class FiscalPeriodSerializer(serializers.Serializer):
    """Serializer for FiscalPeriod model."""

    guid = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    status = serializers.ChoiceField(choices=["open", "closed", "locked"])
    fiscal_year = serializers.IntegerField()

    # Stub - will be fully implemented later
    pass


class TaxRuleSerializer(serializers.Serializer):
    """Serializer for TaxRule model."""

    guid = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)
    code = serializers.CharField(max_length=20)
    rule_type = serializers.ChoiceField(choices=["VALUE", "PERCENT"])
    rate = serializers.DecimalField(max_digits=10, decimal_places=4)
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(required=False, allow_null=True)

    # Stub - will be fully implemented later
    pass


class PaymentTermSerializer(serializers.Serializer):
    """Serializer for PaymentTerm model."""

    guid = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)
    due_days = serializers.IntegerField()
    discount_days = serializers.IntegerField(default=0)
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2)

    # Stub - will be fully implemented later
    pass


class BankAccountSerializer(serializers.Serializer):
    """Serializer for BankAccount model."""

    guid = serializers.UUIDField(read_only=True)
    account = serializers.UUIDField()
    bank_name = serializers.CharField(max_length=255)
    account_number = serializers.CharField(max_length=50)
    currency = serializers.UUIDField()

    # Stub - will be fully implemented later
    pass


class BankStatementSerializer(serializers.Serializer):
    """Serializer for BankStatement model."""

    guid = serializers.UUIDField(read_only=True)
    bank_account = serializers.UUIDField()
    statement_date = serializers.DateField()
    opening_balance = serializers.DecimalField(max_digits=20, decimal_places=10)
    closing_balance = serializers.DecimalField(max_digits=20, decimal_places=10)

    # Stub - will be fully implemented later
    pass


class BankTransactionSerializer(serializers.Serializer):
    """Serializer for BankTransaction model."""

    guid = serializers.UUIDField(read_only=True)
    statement = serializers.UUIDField()
    transaction_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=20, decimal_places=10)
    description = serializers.CharField(max_length=1024)

    # Stub - will be fully implemented later
    pass


class BankReconciliationSerializer(serializers.Serializer):
    """Serializer for BankReconciliation model."""

    guid = serializers.UUIDField(read_only=True)
    bank_account = serializers.UUIDField()
    statement = serializers.UUIDField()
    statement_balance = serializers.DecimalField(max_digits=20, decimal_places=10)
    ledger_balance = serializers.DecimalField(max_digits=20, decimal_places=10)
    status = serializers.ChoiceField(choices=["IN_PROGRESS", "COMPLETED", "ABANDONED"])

    # Stub - will be fully implemented later
    pass


class IntercompanyRelationshipSerializer(serializers.Serializer):
    """Serializer for IntercompanyRelationship model."""

    guid = serializers.UUIDField(read_only=True)
    entity_a = serializers.UUIDField()
    entity_b = serializers.UUIDField()
    relationship_type = serializers.ChoiceField(choices=[
        "PARENT_SUBSIDIARY", "SISTER_COMPANIES", "AFFILIATED",
    ])

    # Stub - will be fully implemented later
    pass


class InterEntityEventSerializer(serializers.Serializer):
    """Serializer for InterEntityEvent model."""

    guid = serializers.UUIDField(read_only=True)
    source_entity = serializers.UUIDField()
    counterparty_entity = serializers.UUIDField()
    status = serializers.ChoiceField(choices=["PROPOSED", "ACCEPTED", "MODIFIED", "REJECTED"])
    source_amount = serializers.DecimalField(max_digits=20, decimal_places=10)

    # Stub - will be fully implemented later
    pass


class AuditEventSerializer(serializers.Serializer):
    """Serializer for AuditEvent model (read-only)."""

    guid = serializers.UUIDField(read_only=True)
    action = serializers.CharField(read_only=True)
    actor = serializers.UUIDField(read_only=True, allow_null=True)
    entity_type = serializers.CharField(read_only=True)
    entity_id = serializers.CharField(read_only=True)
    metadata = serializers.JSONField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)

    # Stub - will be fully implemented later
    pass
