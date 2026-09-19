"""
Client Engagement domain model.

Represents practice ↔ tenant relationships.
"""
import uuid
from django.db import models
from django.conf import settings


class ClientEngagement(models.Model):
    """
    Practice engagement with a client tenant.

    Key points:
    - Explicit relationship between practice and client tenant
    - Status: active, suspended, terminated
    - Practice users access client tenant through this engagement
    - Client can revoke practice access at any time
    - All practice actions logged with engagement_id
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    practice = models.ForeignKey(
        'domain.Practice',
        on_delete=models.CASCADE,
        related_name='engagements'
    )
    tenant = models.ForeignKey(
        'domain.Tenant',
        on_delete=models.CASCADE,
        related_name='practice_engagements'
    )

    # Engagement details
    name = models.CharField(max_length=255, blank=True, help_text='Optional engagement name')
    description = models.TextField(blank=True)

    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Dates
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)

    # Engagement type
    ENGAGEMENT_TYPE_CHOICES = [
        ('bookkeeping', 'Bookkeeping'),
        ('tax_prep', 'Tax Preparation'),
        ('advisory', 'Advisory'),
        ('audit', 'Audit'),
        ('full_service', 'Full Service'),
    ]
    engagement_type = models.CharField(max_length=50, choices=ENGAGEMENT_TYPE_CHOICES, default='bookkeeping')

    # Contact
    practice_contact = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='practice_engagements_as_contact'
    )
    client_contact = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_engagements_as_contact'
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_engagements'
    )

    class Meta:
        db_table = 'client_engagements'
        verbose_name = 'Client Engagement'
        verbose_name_plural = 'Client Engagements'
        unique_together = [['practice', 'tenant']]
        ordering = ['-started_at', '-created_at']
        indexes = [
            models.Index(fields=['practice', 'status']),
            models.Index(fields=['tenant', 'status']),
        ]

    def __str__(self):
        return f'{self.practice.name} ↔ {self.tenant.name} ({self.get_status_display()})'

    @property
    def is_active(self):
        """Check if engagement is active."""
        return self.status == 'active'

    def activate(self):
        """Activate the engagement."""
        from django.utils import timezone
        self.status = 'active'
        self.started_at = timezone.now()
        self.save()

    def terminate(self):
        """Terminate the engagement."""
        from django.utils import timezone
        self.status = 'terminated'
        self.ended_at = timezone.now()
        self.save()

    def get_active_access_grants(self):
        """Get all active access grants for this engagement."""
        return self.access_grants.filter(revoked_at__isnull=True)
