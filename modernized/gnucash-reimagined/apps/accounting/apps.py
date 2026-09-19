"""
Accounting Engine bounded context.

Owns: Account, JournalEntry, JournalLine, Commodity, Currency, ExchangeRate,
      FiscalPeriod, reconciliation, banking, minimal intercompany,
      posting engine, reversal/correction engine, accounting AuditEvent
"""

from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounting"
    label = "accounting"
    verbose_name = "Accounting Engine"
