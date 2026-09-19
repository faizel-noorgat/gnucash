"""
Serializers for accounting engine API.

Implements REST API contracts from the specification.
"""

from decimal import Decimal
from rest_framework import serializers

from accounting_engine.models import (
    Account,
    AccountType,
    AuditEvent,
    BankAccount,
    BankReconciliation,
    BankStatement,
    BankTransaction,
    Commodity,
    Currency,
    ExchangeRate,
    FiscalPeriod,
    InterEntityEvent,
    IntercompanyRelationship,
    JournalEntry,
    JournalLine,
    Lot,
    PaymentTerm,
    ReconcileStatus,
    TaxRule,
)


class CommoditySerializer(serializers.ModelSerializer):
    """Serializer for Commodity model."""

    class Meta:
        model = Commodity
        fields = [
            "guid",
            "namespace",
            "mnemonic",
            "fullname",
            "fraction",
            "decimal_places",
        ]
        read_only_fields = ["guid", "decimal_places"]


class CurrencySerializer(CommoditySerializer):
    """Serializer for Currency model (proxy)."""

    class Meta(CommoditySerializer.Meta):
        model = Currency


class ExchangeRateSerializer(serializers.ModelSerializer):
    """Serializer for ExchangeRate model."""

    from_commodity_code = serializers.CharField(source="from_commodity.mnemonic", read_only=True)
    to_commodity_code = serializers.CharField(source="to_commodity.mnemonic", read_only=True)

    class Meta:
        model = ExchangeRate
        fields = [
            "guid",
            "from_commodity",
            "from_commodity_code",
            "to_commodity",
            "to_commodity_code",
            "rate_date",
            "rate",
            "source",
        ]
        read_only_fields = ["guid"]


class AccountSerializer(serializers.ModelSerializer):
    """
    Serializer for Account model.

    Implements API contract for chart of accounts.
    """

    fundamental_type = serializers.CharField(read_only=True)
    is_ap_ar = serializers.BooleanField(read_only=True)
    commodity_detail = CommoditySerializer(source="commodity", read_only=True)
    balance = serializers.DecimalField(
        max_digits=20,
        decimal_places=10,
        read_only=True,
    )

    class Meta:
        model = Account
        fields = [
            "guid",
            "name",
            "code",
            "description",
            "account_type",
            "fundamental_type",
            "is_ap_ar",
            "commodity",
            "commodity_detail",
            "parent",
            "is_placeholder",
            "is_system",
            "path",
            "level",
            "balance",
            "legal_entity",
        ]
        read_only_fields = ["guid", "path", "level", "fundamental_type", "is_ap_ar"]

    def validate_name(self, value):
        """Validate account name doesn't contain separator."""
        if ":" in value:
            raise serializers.ValidationError(
                "Account name cannot contain ':' (account separator)."
            )
        return value

    def validate(self, data):
        """Validate account constraints."""
        account_type = data.get("account_type")
        parent = data.get("parent")

        # BR-ACCT-010: Root account cannot have parent
        if account_type == AccountType.ROOT and parent is not None:
            raise serializers.ValidationError(
                {"parent": "Root account cannot have a parent account."}
            )

        return data


class JournalLineSerializer(serializers.ModelSerializer):
    """
    Serializer for JournalLine model.

    Dual-field amount/value model (ADR-009).
    """

    account_name = serializers.CharField(source="account.name", read_only=True)
    account_code = serializers.CharField(source="account.code", read_only=True)
    commodity = serializers.CharField(source="account.commodity.mnemonic", read_only=True)

    class Meta:
        model = JournalLine
        fields = [
            "guid",
            "journal_entry",
            "account",
            "account_name",
            "account_code",
            "commodity",
            "amount",
            "value",
            "memo",
            "action",
            "reconcile_status",
            "date_reconciled",
            "online_id",
            "lot",
        ]
        read_only_fields = ["guid", "reconcile_status", "date_reconciled"]


class JournalEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for JournalEntry model.

    Implements API contract for journal entries.
    """

    lines = JournalLineSerializer(many=True, read_only=True)
    transaction_currency_code = serializers.CharField(
        source="transaction_currency.mnemonic",
        read_only=True,
    )
    is_balanced = serializers.BooleanField(read_only=True)
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            "guid",
            "date",
            "date_entered",
            "description",
            "reference",
            "num",
            "transaction_currency",
            "transaction_currency_code",
            "status",
            "is_posted",
            "posted_at",
            "posted_by",
            "source_document",
            "legal_entity",
            "is_balanced",
            "line_count",
            "version",
            "reversal_of",
            "is_reversal",
            "correcting_of",
            "lines",
        ]
        read_only_fields = [
            "guid",
            "date_entered",
            "status",
            "is_posted",
            "posted_at",
            "posted_by",
            "version",
            "is_balanced",
        ]

    def get_line_count(self, obj) -> int:
        return obj.lines.count()


class JournalEntryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating journal entries with lines."""

    lines = JournalLineSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = [
            "date",
            "description",
            "reference",
            "num",
            "transaction_currency",
            "legal_entity",
            "lines",
            "idempotency_key",
        ]

    def create(self, validated_data):
        """Create journal entry with lines atomically."""
        from accounting_engine.services.posting import PostingService

        lines_data = validated_data.pop("lines")
        journal_entry = JournalEntry.objects.create(**validated_data)

        for line_data in lines_data:
            JournalLine.objects.create(journal_entry=journal_entry, **line_data)

        return journal_entry

    def validate(self, data):
        """Validate journal entry can be created."""
        # Check fiscal period
        from accounting_engine.models import FiscalPeriod

        tenant = self.context["request"].user.tenant  # Assuming user has tenant
        legal_entity = data["legal_entity"]
        date = data["date"]

        period = FiscalPeriod.get_period_for_date(tenant, legal_entity, date)
        if period and not period.is_open:
            raise serializers.ValidationError(
                f"Cannot create journal entry in {period.status} fiscal period."
            )

        return data


class FiscalPeriodSerializer(serializers.ModelSerializer):
    """Serializer for FiscalPeriod model."""

    class Meta:
        model = FiscalPeriod
        fields = [
            "guid",
            "name",
            "start_date",
            "end_date",
            "status",
            "fiscal_year",
            "legal_entity",
            "is_open",
            "is_closed",
            "is_locked",
        ]
        read_only_fields = ["guid", "is_open", "is_closed", "is_locked"]


class TaxRuleSerializer(serializers.ModelSerializer):
    """Serializer for TaxRule model."""

    class Meta:
        model = TaxRule
        fields = [
            "guid",
            "name",
            "code",
            "rule_type",
            "rate",
            "effective_from",
            "effective_to",
            "account",
            "is_active",
        ]
        read_only_fields = ["guid"]


class PaymentTermSerializer(serializers.ModelSerializer):
    """Serializer for PaymentTerm model."""

    class Meta:
        model = PaymentTerm
        fields = [
            "guid",
            "name",
            "due_days",
            "discount_days",
            "discount_percent",
            "effective_from",
            "effective_to",
            "is_active",
        ]
        read_only_fields = ["guid"]


class BankAccountSerializer(serializers.ModelSerializer):
    """Serializer for BankAccount model."""

    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            "guid",
            "account",
            "account_name",
            "bank_name",
            "account_number",
            "routing_number",
            "currency",
            "is_active",
            "legal_entity",
        ]
        read_only_fields = ["guid"]


class BankTransactionSerializer(serializers.ModelSerializer):
    """Serializer for BankTransaction model."""

    class Meta:
        model = BankTransaction
        fields = [
            "guid",
            "statement",
            "transaction_date",
            "amount",
            "description",
            "reference",
            "online_id",
            "match_status",
            "matched_journal_line",
            "match_confidence",
        ]
        read_only_fields = ["guid"]


class BankReconciliationSerializer(serializers.ModelSerializer):
    """Serializer for BankReconciliation model."""

    class Meta:
        model = BankReconciliation
        fields = [
            "guid",
            "bank_account",
            "statement",
            "statement_balance",
            "ledger_balance",
            "difference",
            "status",
            "started_at",
            "completed_at",
        ]
        read_only_fields = ["guid", "started_at", "completed_at"]


class IntercompanyRelationshipSerializer(serializers.ModelSerializer):
    """Serializer for IntercompanyRelationship model."""

    class Meta:
        model = IntercompanyRelationship
        fields = [
            "guid",
            "entity_a",
            "entity_b",
            "relationship_type",
            "is_active",
            "effective_from",
            "effective_to",
        ]
        read_only_fields = ["guid"]


class InterEntityEventSerializer(serializers.ModelSerializer):
    """Serializer for InterEntityEvent model."""

    class Meta:
        model = InterEntityEvent
        fields = [
            "guid",
            "source_entity",
            "counterparty_entity",
            "source_journal_entry",
            "counterpart_journal_entry",
            "status",
            "mismatch_status",
            "source_amount",
            "counterpart_amount",
            "currency",
            "proposed_at",
            "accepted_at",
        ]
        read_only_fields = ["guid", "proposed_at", "accepted_at"]


class LotSerializer(serializers.ModelSerializer):
    """Serializer for Lot model."""

    balance = serializers.DecimalField(max_digits=20, decimal_places=10, read_only=True)
    value = serializers.DecimalField(max_digits=20, decimal_places=10, read_only=True)

    class Meta:
        model = Lot
        fields = [
            "guid",
            "title",
            "notes",
            "is_closed",
            "account",
            "invoice",
            "balance",
            "value",
        ]
        read_only_fields = ["guid", "is_closed", "balance", "value"]


class AuditEventSerializer(serializers.ModelSerializer):
    """Serializer for AuditEvent model."""

    class Meta:
        model = AuditEvent
        fields = [
            "guid",
            "action",
            "actor",
            "entity_type",
            "entity_id",
            "metadata",
            "timestamp",
            "ip_address",
        ]
        read_only_fields = fields
