"""
Practice domain model.

Represents an accounting firm / advisory practice that manages multiple client tenants.
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
