from __future__ import annotations

from notifications.models import Notification, NotificationType


class NotificationService:
    """Service layer for notification operations."""

    @staticmethod
    def create(
        tenant,
        user,
        notification_type: NotificationType | str,
        title: str,
        body: str,
    ) -> Notification:
        """Create a new notification for a user within a tenant.

        Args:
            tenant: The Tenant instance this notification belongs to.
            user: The User instance to notify.
            notification_type: The type of notification (NotificationType enum or string).
            title: The notification title.
            body: The notification body text.

        Returns:
            The created Notification instance.
        """
        return Notification.objects.create(
            tenant=tenant,
            user=user,
            type=notification_type,
            title=title,
            body=body,
        )
