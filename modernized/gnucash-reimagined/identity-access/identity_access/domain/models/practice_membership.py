"""
Practice Membership domain model.

Represents user ↔ practice relationships with practice-level roles.
"""
import uuid
from django.db import models
from django.conf import settings


class PracticeMembership(models.Model):
    """
    User membership in a practice with practice-level role.

    Key points:
    - Links users to practices
    - Practice-level roles: partner, manager, senior, staff
    - Practice users can access multiple client tenants through engagements
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='practice_memberships'
    )
    practice = models.ForeignKey(
        'domain.Practice',
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    # Practice-level role
    PRACTICE_ROLE_CHOICES = [
        ('partner', 'Partner'),
        ('manager', 'Manager'),
        ('senior', 'Senior Accountant'),
        ('staff', 'Staff Accountant'),
        ('admin', 'Practice Administrator'),
    ]
    role = models.CharField(max_length=50, choices=PRACTICE_ROLE_CHOICES, default='staff')

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
        related_name='sent_practice_invitations'
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    invitation_token = models.CharField(max_length=100, unique=True, null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'practice_memberships'
        verbose_name = 'Practice Membership'
        verbose_name_plural = 'Practice Memberships'
        unique_together = [['user', 'practice']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'practice']),
            models.Index(fields=['practice', 'status']),
            models.Index(fields=['invitation_token']),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.practice.name} ({self.get_role_display()})'

    @property
    def is_active(self):
        """Check if membership is active."""
        return self.status == 'active'

    def accept_invitation(self):
        """Accept the practice membership invitation."""
        from django.utils import timezone
        self.status = 'active'
        self.accepted_at = timezone.now()
        self.save()
