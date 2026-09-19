"""
Notification Service

Handles notification creation, delivery, and preferences.
"""
from django.db import transaction
from django.utils import timezone
from ..models import Notification, NotificationPreference


class NotificationService:
    """
    Service for notification management operations.

    Responsibilities:
    - Create and send notifications
    - Manage notification preferences
    - Track notification delivery and read status
    """

    @staticmethod
    @transaction.atomic
    def create_notification(recipient, title, message, notification_type='info',
                            tenant=None, action_url='', delivery_channels=None,
                            metadata=None):
        """
        Create a new notification.

        Args:
            recipient: User receiving notification
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            tenant: Optional Tenant context
            action_url: URL to navigate to when clicked
            delivery_channels: List of channels (email, in_app, push)
            metadata: Additional metadata dict

        Returns:
            Created Notification object
        """
        if delivery_channels is None:
            delivery_channels = ['in_app']

        notification = Notification.objects.create(
            recipient=recipient,
            tenant=tenant,
            notification_type=notification_type,
            title=title,
            message=message,
            delivery_channels=delivery_channels,
            action_url=action_url,
            metadata=metadata or {}
        )

        # Queue notification for delivery
        NotificationService._queue_notification_delivery(notification)

        return notification

    @staticmethod
    def _queue_notification_delivery(notification):
        """
        Queue notification for async delivery via Celery.

        Args:
            notification: Notification object
        """
        # In production, this would queue a Celery task
        # from ..tasks import deliver_notification_task
        # deliver_notification_task.delay(notification.guid)
        pass

    @staticmethod
    def send_email_notification(notification):
        """
        Send notification via email.

        Args:
            notification: Notification object
        """
        from django.core.mail import send_mail
        from django.conf import settings

        # Check user preferences
        if not NotificationService._should_send_email(notification):
            return

        subject = notification.title
        message = notification.message

        if notification.action_url:
            message += f'\n\nView details: {notification.action_url}'

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [notification.recipient.email],
                fail_silently=False
            )
            notification.email_status = 'sent'
            notification.sent_at = timezone.now()
            notification.save(update_fields=['email_status', 'sent_at'])
        except Exception as e:
            notification.email_status = 'failed'
            notification.save(update_fields=['email_status'])
            raise

    @staticmethod
    def _should_send_email(notification):
        """
        Check if email should be sent based on user preferences.

        Args:
            notification: Notification object

        Returns:
            True if email should be sent, False otherwise
        """
        # Get user preferences
        prefs = NotificationPreference.objects.filter(
            user=notification.recipient,
            tenant=notification.tenant
        ).first()

        if not prefs:
            # Get global preferences
            prefs = NotificationPreference.objects.filter(
                user=notification.recipient,
                tenant__isnull=True
            ).first()

        if prefs:
            return prefs.should_deliver(notification.notification_type, 'email')

        return True  # Default to sending

    @staticmethod
    def mark_as_read(notification):
        """
        Mark notification as read.

        Args:
            notification: Notification object
        """
        notification.mark_as_read()

    @staticmethod
    def mark_all_as_read(recipient, tenant=None):
        """
        Mark all notifications as read for user.

        Args:
            recipient: User object
            tenant: Optional Tenant to scope to
        """
        queryset = Notification.objects.filter(
            recipient=recipient,
            is_read=False
        )

        if tenant:
            queryset = queryset.filter(tenant=tenant)

        queryset.update(
            is_read=True,
            read_at=timezone.now()
        )

    @staticmethod
    def get_unread_count(recipient, tenant=None):
        """
        Get count of unread notifications.

        Args:
            recipient: User object
            tenant: Optional Tenant to scope to

        Returns:
            Count of unread notifications
        """
        queryset = Notification.objects.filter(
            recipient=recipient,
            is_read=False
        )

        if tenant:
            queryset = queryset.filter(tenant=tenant)

        return queryset.count()

    @staticmethod
    def update_preferences(user, tenant, preferences):
        """
        Update notification preferences.

        Args:
            user: User object
            tenant: Optional Tenant (None for global preferences)
            preferences: Dict of notification preferences

        Returns:
            Updated NotificationPreference object
        """
        prefs, created = NotificationPreference.objects.get_or_create(
            user=user,
            tenant=tenant
        )

        prefs.preferences = preferences
        prefs.save()

        return prefs

    @staticmethod
    def get_preferences(user, tenant=None):
        """
        Get notification preferences.

        Args:
            user: User object
            tenant: Optional Tenant

        Returns:
            NotificationPreference object or None
        """
        return NotificationPreference.objects.filter(
            user=user,
            tenant=tenant
        ).first()
