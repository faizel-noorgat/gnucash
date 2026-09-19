"""
API Token domain model.

Represents API tokens for integrations with scoped permissions.
"""
import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone


class ApiToken(models.Model):
    """
    API token for integrations.

    Key points:
    - Scoped to specific permissions
    - Can expire
    - Can be revoked
    - Audit trail of usage
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User who owns this token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_tokens'
    )

    # Tenant scope (optional - if None, token has access to all user's tenants)
    tenant = models.ForeignKey(
        'identity.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='api_tokens'
    )

    # Token information
    name = models.CharField(max_length=255, help_text='Descriptive name for this token')
    token = models.CharField(max_length=128, unique=True, editable=False)
    token_prefix = models.CharField(max_length=8, editable=False)  # First 8 chars for identification

    # Permissions (JSON array of permission codenames)
    permissions = models.JSONField(default=list, help_text='List of permission codenames')

    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revoked_tokens'
    )

    # Usage tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_api_tokens'
    )

    class Meta:
        db_table = 'api_tokens'
        verbose_name = 'API Token'
        verbose_name_plural = 'API Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} ({self.token_prefix}...)'

    def save(self, *args, **kwargs):
        """Generate token on first save."""
        if not self.token:
            self.token = self._generate_token()
            self.token_prefix = self.token[:8]
        super().save(*args, **kwargs)

    def _generate_token(self):
        """Generate a secure random token.

        The payload is sized to fit the column it is written into. token_urlsafe
        emits 4 base64 characters per 3 bytes, so the previous 96 bytes produced
        exactly 128 characters - the full width of the `token` field - and the
        'fva_' prefix then pushed the result 4 characters past it. Every
        ApiToken.objects.create() therefore died with "value too long for type
        character varying(128)". 80 bytes (640 bits of entropy, far beyond what
        a token needs) leaves the value at 112 characters.
        """
        return f'fva_{secrets.token_urlsafe(80)}'

    @property
    def is_expired(self):
        """Check if token has expired."""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if token is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def revoke(self, revoked_by_user):
        """Revoke this token."""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.revoked_by = revoked_by_user
        self.save()

    def record_usage(self, ip_address=None):
        """Record token usage."""
        self.last_used_at = timezone.now()
        self.last_used_ip = ip_address
        self.usage_count += 1
        self.save(update_fields=['last_used_at', 'last_used_ip', 'usage_count'])
