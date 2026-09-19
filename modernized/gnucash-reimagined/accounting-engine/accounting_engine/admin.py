"""Django admin configuration for accounting engine."""

from django.contrib import admin

from accounting_engine.models import (
    Account,
    AuditEvent,
    BankAccount,
    BankReconciliation,
    BankStatement,
    BankTransaction,
    Commodity,
    ExchangeRate,
    FiscalPeriod,
    InterEntityEvent,
    IntercompanyRelationship,
    JournalEntry,
    JournalLine,
    Lot,
    PaymentTerm,
    TaxRule,
)


@admin.register(Commodity)
class CommodityAdmin(admin.ModelAdmin):
    list_display = ["mnemonic", "fullname", "namespace", "fraction"]
    list_filter = ["namespace"]
    search_fields = ["mnemonic", "fullname"]


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["from_commodity", "to_commodity", "rate_date", "rate", "source"]
    list_filter = ["rate_date", "source"]
    search_fields = ["from_commodity__mnemonic", "to_commodity__mnemonic"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "account_type", "commodity", "parent", "is_system"]
    list_filter = ["account_type", "is_system", "legal_entity"]
    search_fields = ["name", "code", "description"]
    raw_id_fields = ["parent", "commodity"]


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ["num", "date", "description", "status", "is_posted", "legal_entity"]
    list_filter = ["status", "is_posted", "legal_entity"]
    search_fields = ["description", "reference", "num"]
    date_hierarchy = "date"
    raw_id_fields = ["transaction_currency", "source_document"]


@admin.register(JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = ["journal_entry", "account", "amount", "value", "reconcile_status"]
    list_filter = ["reconcile_status"]
    search_fields = ["memo"]
    raw_id_fields = ["journal_entry", "account", "lot"]


@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(admin.ModelAdmin):
    list_display = ["name", "start_date", "end_date", "status", "fiscal_year"]
    list_filter = ["status", "fiscal_year"]
    date_hierarchy = "start_date"


@admin.register(TaxRule)
class TaxRuleAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "rule_type", "rate", "effective_from", "is_active"]
    list_filter = ["rule_type", "is_active"]
    search_fields = ["name", "code"]


@admin.register(PaymentTerm)
class PaymentTermAdmin(admin.ModelAdmin):
    list_display = ["name", "due_days", "discount_days", "discount_percent", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ["bank_name", "account_number", "account", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["bank_name", "account_number"]


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ["transaction_date", "description", "amount", "match_status"]
    list_filter = ["match_status"]
    search_fields = ["description", "reference"]
    date_hierarchy = "transaction_date"


@admin.register(BankReconciliation)
class BankReconciliationAdmin(admin.ModelAdmin):
    list_display = ["bank_account", "statement", "status", "started_at"]
    list_filter = ["status"]
    date_hierarchy = "started_at"


@admin.register(IntercompanyRelationship)
class IntercompanyRelationshipAdmin(admin.ModelAdmin):
    list_display = ["entity_a", "entity_b", "relationship_type", "is_active"]
    list_filter = ["relationship_type", "is_active"]


@admin.register(InterEntityEvent)
class InterEntityEventAdmin(admin.ModelAdmin):
    list_display = ["source_entity", "counterparty_entity", "status", "mismatch_status"]
    list_filter = ["status", "mismatch_status"]
    date_hierarchy = "proposed_at"


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ["title", "account", "is_closed"]
    list_filter = ["is_closed"]
    search_fields = ["title"]


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["action", "entity_type", "entity_id", "actor", "timestamp"]
    list_filter = ["action", "entity_type"]
    search_fields = ["entity_id", "metadata"]
    date_hierarchy = "timestamp"
    readonly_fields = [
        "guid",
        "tenant",
        "legal_entity",
        "action",
        "actor",
        "entity_type",
        "entity_id",
        "metadata",
        "timestamp",
        "ip_address",
        "user_agent",
    ]
