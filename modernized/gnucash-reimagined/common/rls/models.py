"""
Row Level Security (RLS) infrastructure for multi-tenancy.

This module provides centralized RLS support for the application.
All tenant-scoped models should use the mixins and utilities here.
"""

from django.db import models


class TenantScopedModel(models.Model):
    """
    Abstract base model for tenant-scoped entities.

    All models that belong to a specific tenant should inherit from this.
    Provides tenant_id foreign key and common tenant-scoped query methods.
    """

    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
    )

    class Meta:
        abstract = True

    @classmethod
    def for_tenant(cls, tenant):
        """Get queryset filtered to specific tenant."""
        return cls.objects.filter(tenant=tenant)


class EntityScopedModel(TenantScopedModel):
    """
    Abstract base model for legal-entity-scoped entities.

    Some accounting data is scoped not just to a tenant but to a specific
    legal entity within the tenant (e.g., accounts, journal entries).
    """

    legal_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
        null=True,  # Some entities may not be entity-scoped
        blank=True,
    )

    class Meta:
        abstract = True

    @classmethod
    def for_entity(cls, legal_entity):
        """Get queryset filtered to specific legal entity."""
        return cls.objects.filter(legal_entity=legal_entity)


class ImmutablePostedModel(models.Model):
    """
    Abstract base model for posted accounting records that are immutable.

    Once posted, financial facts cannot be changed. Corrections must use
    reversal/correcting entries. This is enforced via:
    1. Application-level guards (save() method checks)
    2. Database-level BEFORE UPDATE/DELETE triggers (ADR-010)
    """

    is_posted = models.BooleanField(default=False, db_index=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        "identity.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(class)s_posted",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Prevent modification of posted records."""
        if self.pk and self.is_posted:
            # Check if this is an update to a posted record
            try:
                original = self.__class__.objects.get(pk=self.pk)
                if original.is_posted:
                    raise ValueError(
                        f"Cannot modify posted {self.__class__.__name__}. "
                        "Use reversal/correcting entries instead."
                    )
            except self.__class__.DoesNotExist:
                pass  # New record, allow save
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of posted records."""
        if self.is_posted:
            raise ValueError(
                f"Cannot delete posted {self.__class__.__name__}. "
                "Use reversal/correcting entries instead."
            )
        super().delete(*args, **kwargs)
