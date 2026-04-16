from __future__ import annotations

from celery import shared_task


@shared_task(name='investments.sync_prices')
def sync_prices():
    pass
