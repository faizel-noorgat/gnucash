"""
Notification domain model.

Represents notifications (email, in-app) and user preferences.
"""
import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Notification for users (email, in-app).

    Key points:
    - Email notifications sent asynchronously via Celery
    - In-app notifications for polling (30s intervals in v1)
    - Notification types: approval, reminder, alert, system
    - Read/unread tracking
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Recipient
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Tenant context (optional)
    tenant = models.ForeignKey(
        'domain.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    # Notification content
    NOTIFICATION_TYPE_CHOICES = [
        ('approval', 'Approval Required'),
        ('reminder', 'Reminder'),
        ('alert', 'Alert'),
        ('system', 'System'),
        ('invitation', 'Invitation'),
        ('info', 'Information'),
    ]
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES, default='info')

    title = models.CharField(max_length=255)
    message = models.TextField()

    # Delivery channels
    delivery_channels = models.JSONField(
        default=list,
        help_text='List of delivery channels: email, in_app, push'
    )

    # Status
    CHANNEL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    email_status = models.CharField(max_length=20, choices=CHANNEL_STATUS_CHOICES, default='pending')
    in_app_status = models.CharField(max_length=20, choices=CHANNEL_STATUS_CHOICES, default='pending')

    # Read tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Action URL
    action_url = models.URLField(blank=True, help_text='URL to navigate to when notification is clicked')

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f'{self.title} → {self.recipient.email}'

    def mark_as_read(self):
        """Mark notification as read."""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class NotificationPreference(models.Model):
    """
    User notification preferences.

    Key points:
    - Per-user notification settings
    - Can be scoped to tenant or global
    - Controls which notification types are delivered via which channels
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Tenant scope (optional - if None, applies globally)
    tenant = models.ForeignKey(
        'domain.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notification_preferences'
    )

    # Preferences per notification type
    preferences = models.JSONField(
        default=dict,
        help_text='Dict of notification_type -> {email: bool, in_app: bool, push: bool}'
    )

    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    quiet_hours_timezone = models.CharField(max_length=50, default='UTC')

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
        unique_together = [['user', 'tenant']]
        indexes = [
            models.Index(fields=['user', 'tenant']),
        ]

    def __str__(self):
        if self.tenant:
            return f'{self.user.email} - {self.tenant.name}'
        return f'{self.user.email} (global)'

    def should_deliver(self, notification_type, channel):
        """Check if notification should be delivered via channel."""
        if notification_type not in self.preferences:
            return True  # Default to delivering
        type_prefs = self.preferences[notification_type]
        return type_prefs.get(channel, True)
