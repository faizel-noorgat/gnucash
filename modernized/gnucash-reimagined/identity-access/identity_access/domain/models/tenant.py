"""
Tenant domain model.

Represents a workspace that represents an SME/customer organization.
"""
import uuid
from django.db import models
from django.conf import settings


class Tenant(models.Model):
    """
    Tenant represents a workspace / SME customer organization.

    Key points:
    - A Tenant represents an SME/customer organization
    - Multi-tenancy via shared-schema PostgreSQL with RLS
    - Defense-in-depth: ORM default filters + RLS policies
    - Legal entities within tenant own independent ledgers

    This is NOT an accounting practice. Practices are separate entities
    that manage multiple client tenants through explicit engagements.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic information
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Organization details
    organization_name = models.CharField(max_length=255, blank=True)
    business_registration_number = models.CharField(max_length=100, blank=True)
    tax_identification_number = models.CharField(max_length=100, blank=True)

    # Contact information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)

    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Singapore')

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    # Settings
    default_currency = models.CharField(max_length=3, default='SGD')
    fiscal_year_start_month = models.IntegerField(default=1)  # January

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tenants'
    )

    class Meta:
        db_table = 'tenants'
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name
