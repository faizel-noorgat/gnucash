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


class TenantDerivedChildModel(models.Model):
    """
    Abstract base for a child row whose tenant is inherited from its parent.

    These rows are genuine tenant-owned data - ledger lines, document lines,
    attachments, extractions - but they reach a tenant through a parent
    foreign key rather than carrying their own ``tenant_id``. Policing them
    with an ``EXISTS`` subquery against the parent would work, but it makes
    every policy a correlated subquery and leaves the tenancy denormalised
    nowhere, so the row carries no statement of its own about which tenant it
    belongs to.

    So the tenant is materialised on the child, and the child is kept in
    agreement with its parent by the database rather than by convention:

    * ``derive_tenant_id()`` fills ``tenant_id`` in from the parent, and
      ``save()`` calls it - so an ordinary caller constructs the row and saves
      it, and never chooses a tenant at all.
    * A **composite foreign key** ``(parent_id, tenant_id) ->
      parent(id, tenant_id)`` is added by migration ``rls/0003``. That is what
      makes ``child.tenant_id`` disagreeing with ``child.parent.tenant_id``
      *impossible* rather than merely discouraged, and it holds against raw
      SQL that never went through this class.

    Neither half is redundant. The mixin is convenience - it is what stops
    every caller having to know the field exists. The composite foreign key is
    the guarantee, and it is the only one of the two that a raw ``INSERT``
    cannot ignore.

    Subclasses declare their own ``tenant`` field, and must give it the same
    *shape* the parent has - a ``ForeignKey`` where the parent's is a
    ``ForeignKey``, a bare ``UUIDField`` where the parent's is a bare
    ``UUIDField``. This mixin deliberately declares no field of its own,
    because a child whose tenancy is derived from a parent has to accept
    exactly what the parent holds. A child typed more strictly than its parent
    is not a safer child: it makes rows the parent accepts impossible to
    attach anything to, which is an inconsistency rather than a constraint.
    """

    #: Name of the FK field whose parent owns this row's tenancy.
    tenant_parent_field: str = ""

    class Meta:
        abstract = True

    def derive_tenant_id(self):
        """Populate ``tenant_id`` from the parent, unless it is already set.

        Raises rather than storing a NULL when the parent is absent. A child
        with no parent has no tenant, and a NULL ``tenant_id`` matches no
        policy - the row would exist but be invisible to every reader,
        including the one that just wrote it. A loud failure at the write is
        better than a row nobody can ever find.
        """
        if not hasattr(self, "tenant_id"):
            raise ValueError(
                f"{type(self).__name__} inherits TenantDerivedChildModel but "
                f"declares no 'tenant' field, so its tenant cannot be stored."
            )

        if self.tenant_id is not None:
            return self.tenant_id

        field_name = self.tenant_parent_field
        if not field_name:
            raise ValueError(
                f"{type(self).__name__} derives its tenant from a parent but "
                f"declares no tenant_parent_field."
            )

        parent_id = getattr(self, f"{field_name}_id")
        if parent_id is None:
            raise ValueError(
                f"{type(self).__name__} has no '{field_name}' set, so its tenant "
                f"cannot be derived. Set the parent before saving."
            )

        parent_model = self._meta.get_field(field_name).related_model
        self.tenant_id = parent_model._default_manager.values_list(
            "tenant_id", flat=True
        ).get(pk=parent_id)
        return self.tenant_id

    def save(self, *args, **kwargs):
        self.derive_tenant_id()
        super().save(*args, **kwargs)


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
