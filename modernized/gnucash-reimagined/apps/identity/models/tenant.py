"""
Tenant and LegalEntity domain models.

Represents a workspace (SME/customer organization) and the legal entities
that own independent ledgers within that tenant.
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


class LegalEntity(models.Model):
    """
    Legal entity that owns an independent ledger within a tenant.

    Key points:
    - Each legal entity has its own ledger (chart of accounts, journal entries)
    - Multiple legal entities can exist within a single tenant
    - Intercompany relationships link legal entities within a tenant
    - Each entity has its own base currency
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant relationship
    tenant = models.ForeignKey(
        'identity.Tenant',
        on_delete=models.CASCADE,
        related_name='legal_entities'
    )

    # Basic information
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_identification_number = models.CharField(max_length=100, blank=True)

    # Entity type
    ENTITY_TYPE_CHOICES = [
        ('company', 'Company'),
        ('partnership', 'Partnership'),
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('trust', 'Trust'),
        ('non_profit', 'Non-Profit'),
        ('government', 'Government Entity'),
        ('other', 'Other'),
    ]
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES, default='company')

    # Currency and accounting
    base_currency = models.CharField(max_length=3, default='SGD')
    fiscal_year_start_month = models.IntegerField(default=1)  # January
    accounting_standard = models.CharField(max_length=50, default='IFRS')

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
    is_considered_intercompany = models.BooleanField(default=False)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_legal_entities'
    )

    class Meta:
        db_table = 'legal_entities'
        verbose_name = 'Legal Entity'
        verbose_name_plural = 'Legal Entities'
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['registration_number']),
        ]

    def __str__(self):
        return f'{self.name} ({self.tenant.name})'
