"""
Party model - unified entity for customers, vendors, employees, connected entities
"""
from django.db import models
from django.conf import settings
import uuid


class PartyRole(models.TextChoices):
    """Roles a party can have"""
    CUSTOMER = 'CUSTOMER', 'Customer'
    VENDOR = 'VENDOR', 'Vendor'
    EMPLOYEE = 'EMPLOYEE', 'Employee'
    CONNECTED_ENTITY = 'CONNECTED_ENTITY', 'Connected Entity'


class Party(models.Model):
    """
    Unified party entity representing customers, vendors, employees, or connected entities.

    A party may have multiple roles and belongs to a tenant.
    """
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'identity.Tenant',
        on_delete=models.CASCADE,
        related_name='parties',
        db_index=True
    )

    # Basic information
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True)

    # Roles (a party can have multiple roles)
    roles = models.JSONField(default=list, help_text="List of PartyRole values")

    # Contact information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    # Address (stored as JSON for flexibility)
    address = models.JSONField(default=dict, blank=True, help_text="Structured address object")

    # Tax and currency
    tax_id = models.CharField(max_length=100, blank=True, help_text="Tax identification number")
    currency = models.ForeignKey(
        'accounting.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parties'
    )

    # Default terms
    payment_terms = models.ForeignKey(
        'accounting.PaymentTerm',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parties'
    )
    tax_table = models.ForeignKey(
        'accounting.TaxRule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parties'
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_parties'
    )

    class Meta:
        db_table = 'business_documents_party'
        verbose_name = 'Party'
        verbose_name_plural = 'Parties'
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'name']),
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.display_name or self.name

    def save(self, *args, **kwargs):
        # Auto-set display_name if not provided
        if not self.display_name:
            self.display_name = self.name
        super().save(*args, **kwargs)

    def has_role(self, role: PartyRole) -> bool:
        """Check if party has a specific role"""
        return role in self.roles

    def add_role(self, role: PartyRole):
        """Add a role to the party"""
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, role: PartyRole):
        """Remove a role from the party"""
        if role in self.roles:
            self.roles.remove(role)

    @property
    def is_customer(self) -> bool:
        return self.has_role(PartyRole.CUSTOMER)

    @property
    def is_vendor(self) -> bool:
        return self.has_role(PartyRole.VENDOR)

    @property
    def is_employee(self) -> bool:
        return self.has_role(PartyRole.EMPLOYEE)
