from __future__ import annotations

from celery import shared_task


@shared_task(name='billing.sync_stripe_data')
def sync_stripe_data():
    """Sync local subscription data with Stripe."""
    pass
