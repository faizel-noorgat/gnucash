"""
Advisor Access Grant domain model.

Represents explicit, revocable, auditable access from practice to client tenant.
"""
import uuid
from django.db import models
from django.conf import settings


class AdvisorAccessGrant(models.Model):
    """
    Explicit access grant from practice to client tenant.

    Key points:
    - Explicit, revocable, and auditable access
    - Grants practice user access to client tenant with specific role
    - Time-bound (can have expiration)
    - All grants logged in audit trail
    - Client can revoke at any time
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    engagement = models.ForeignKey(
        'domain.ClientEngagement',
        on_delete=models.CASCADE,
        related_name='access_grants'
    )
    practice_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='advisor_access_grants'
    )

    # Role within client tenant
    tenant_role = models.ForeignKey(
        'domain.Role',
        on_delete=models.CASCADE,
        related_name='advisor_access_grants'
    )

    # Access scope (optional - if None, access to all entities in tenant)
    scoped_entity = models.ForeignKey(
        'domain.LegalEntity',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='advisor_access_grants'
    )

    # Time bounds
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revoked_advisor_access_grants'
    )
    revocation_reason = models.TextField(blank=True)

    # Granted by
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_advisor_access'
    )

    # Access reason
    reason = models.TextField(blank=True, help_text='Reason for granting access')

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'advisor_access_grants'
        verbose_name = 'Advisor Access Grant'
        verbose_name_plural = 'Advisor Access Grants'
        ordering = ['-granted_at']
        indexes = [
            models.Index(fields=['engagement', 'practice_user']),
            models.Index(fields=['practice_user', 'revoked_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'{self.practice_user.email} → {self.engagement.tenant.name} ({self.tenant_role.name})'

    @property
    def is_active(self):
        """Check if access grant is active."""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None:
            from django.utils import timezone
            if timezone.now() > self.expires_at:
                return False
        return True

    @property
    def is_expired(self):
        """Check if access grant has expired."""
        if self.expires_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def revoke(self, revoked_by_user, reason=''):
        """Revoke this access grant."""
        from django.utils import timezone
        self.revoked_at = timezone.now()
        self.revoked_by = revoked_by_user
        self.revocation_reason = reason
        self.save()
