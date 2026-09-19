"""
Practice domain models.

Represents an accounting firm / advisory practice that manages multiple client
tenants through explicit engagements, plus the membership and access grant
models that implement the advisor access pattern.
"""
import uuid
from django.db import models
from django.conf import settings


class Practice(models.Model):
    """
    Accounting firm / advisory practice.

    Key points:
    - A Practice manages multiple client Tenants through explicit engagements
    - Practice is separate from Tenant (tenant = SME customer)
    - Practice users authenticate → see list of client engagements
    - Practice users select client → context switches to that tenant
    - All practice actions logged with practice_id and engagement_id
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic information
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Contact information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Singapore')

    # Business details
    business_registration_number = models.CharField(max_length=100, blank=True)
    tax_identification_number = models.CharField(max_length=100, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_practices'
    )

    class Meta:
        db_table = 'practices'
        verbose_name = 'Practice'
        verbose_name_plural = 'Practices'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def get_active_engagements(self):
        """Get all active client engagements for this practice."""
        return self.engagements.filter(status='active')

    def get_members(self):
        """Get all practice members."""
        return self.memberships.filter(status='active')


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
        'identity.Practice',
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
        'identity.Practice',
        on_delete=models.CASCADE,
        related_name='engagements'
    )
    tenant = models.ForeignKey(
        'identity.Tenant',
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
        'identity.ClientEngagement',
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
        'identity.Role',
        on_delete=models.CASCADE,
        related_name='advisor_access_grants'
    )

    # Access scope (optional - if None, access to all entities in tenant)
    scoped_entity = models.ForeignKey(
        'identity.LegalEntity',
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

    def revoke(self, revoked_by, reason=''):
        """Revoke this access grant.

        The parameter is named after the field it sets: callers revoke a grant
        naming the revoking user, and `revoke(revoked_by=...)` is how the
        acceptance contract (BR-PRACTICE-002) calls it.
        """
        from django.utils import timezone
        self.revoked_at = timezone.now()
        self.revoked_by = revoked_by
        self.revocation_reason = reason
        self.save()
