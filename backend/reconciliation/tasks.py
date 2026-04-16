from __future__ import annotations

from celery import shared_task


@shared_task(name='reconciliation.auto_clear')
def auto_clear(account_id, target_balance, end_date):
    """Auto-clear matching splits for a reconciliation session."""
    pass
