from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from audit.models import AuditLog


@shared_task(name='audit.purge_old_logs')
def purge_old_logs(retention_days: int = 2555) -> int:
    """Delete audit logs older than the retention period.

    Args:
        retention_days: Number of days to retain audit logs. Defaults to 2555 (~7 years).

    Returns:
        Number of deleted log entries.
    """
    cutoff = timezone.now() - timedelta(days=retention_days)
    count, _ = AuditLog.objects.filter(timestamp__lt=cutoff).delete()
    return count
