from __future__ import annotations

from celery import shared_task


@shared_task(name='notifications.send_digests')
def send_digests() -> None:
    """Send notification digests to users.

    This task batches unread notifications per user and sends them
    via their configured channels (in-app, email, push).
    """
    pass
