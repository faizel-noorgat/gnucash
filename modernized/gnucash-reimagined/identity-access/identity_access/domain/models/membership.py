"""
Membership domain model.

Represents user ↔ tenant relationships with roles.
"""
import uuid
from django.db import models
from django.conf import settings


class Membership(models.Model):
    """
    User membership in a tenant with specific role(s).

    Key points:
    - Links users to tenants
    - Can have multiple memberships (user in multiple tenants)
    - Each membership has a role that determines permissions
    - Invitation workflow for adding new members
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    tenant = models.ForeignKey(
        'domain.Tenant',
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    # Role
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Administrator'),
        ('accountant', 'Accountant'),
        ('bookkeeper', 'Bookkeeper'),
        ('ap_clerk', 'AP Clerk'),
        ('ar_clerk', 'AR Clerk'),
        ('approver', 'Approver'),
        ('auditor', 'Auditor'),
        ('viewer', 'Viewer'),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='viewer')

    # Status
    STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('deactivated', 'Deactivated'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')

    # Invitation
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations'
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    invitation_token = models.CharField(max_length=100, unique=True, null=True, blank=True)

    # Entity scope (optional - if None, role applies to all entities in tenant)
    scoped_entity = models.ForeignKey(
        'domain.LegalEntity',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='scoped_memberships'
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'memberships'
        verbose_name = 'Membership'
        verbose_name_plural = 'Memberships'
        unique_together = [['user', 'tenant', 'scoped_entity']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'tenant']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['invitation_token']),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.tenant.name} ({self.get_role_display()})'

    @property
    def is_active(self):
        """Check if membership is active."""
        return self.status == 'active'

    def accept_invitation(self):
        """Accept the membership invitation."""
        from django.utils import timezone
        self.status = 'active'
        self.accepted_at = timezone.now()
        self.save()
