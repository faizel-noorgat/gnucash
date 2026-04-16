from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone


FREQUENCY_MAP = {
    'DAILY': lambda d: d + timedelta(days=1),
    'WEEKLY': lambda d: d + timedelta(weeks=1),
    'MONTHLY': lambda d: (d.replace(day=1) + timedelta(days=32)).replace(day=1),
    'QUARTERLY': lambda d: (d.replace(day=1) + timedelta(days=92)).replace(day=1),
    'YEARLY': lambda d: d.replace(year=d.year + 1),
}


@shared_task(name='recurring.run_scheduled_transactions')
def run_scheduled_transactions():
    from recurring.models import RecurringTransaction

    today = timezone.now().date()
    due = RecurringTransaction.objects.filter(enabled=True, next_run__lte=today)
    for rt in due:
        # Placeholder: create transaction from template
        calc_next = FREQUENCY_MAP.get(rt.frequency, lambda d: d + timedelta(days=1))
        rt.last_run = timezone.now()
        rt.next_run = calc_next(rt.next_run)
        rt.save()
