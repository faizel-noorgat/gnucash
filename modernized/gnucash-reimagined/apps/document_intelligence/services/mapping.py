"""Mapping service — learned accounting mappings management.

Responsibilities:
1. CRUD operations for AccountingMapping (organizational knowledge)
2. Retirement workflow (soft-delete with audit trail)
3. Lookup mappings by supplier/description/amount
4. NEVER auto-create mappings from AI suggestions - human approval required

Design:
- Mappings are explicit organizational knowledge (BR-DI-007)
- AI suggestions trace back to mappings, not LLM memory
- All mutations preserve audit trail (created_by, approved_by, retired_by)
- Tenant-scoped via tenant_id (BR-DI-010)

Implements behavior-contract rules:
- BR-DI-007: mappings are explicit organizational knowledge, not LLM memory
- BR-DI-008: full provenance captured
- BR-DI-010: tenant-scoped
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import AccountingMapping, MappingConfidence

logger = logging.getLogger(__name__)


class MappingService:
    """Manages accounting mappings (organizational knowledge).

    Usage:
        service = MappingService()
        mapping = service.create_mapping(tenant_id=..., ...)
        mappings = service.find_mappings(tenant_id=..., supplier_party_id=...)
    """

    def create_mapping(
        self,
        *,
        tenant_id: uuid.UUID,
        legal_entity_id: uuid.UUID | None = None,
        supplier_party_id: uuid.UUID | None = None,
        description_pattern: str = "",
        amount_range_min: str | None = None,
        amount_range_max: str | None = None,
        target_account_id: uuid.UUID,
        target_tax_rule_id: uuid.UUID | None = None,
        target_dimension_id: uuid.UUID | None = None,
        confidence: str = MappingConfidence.MEDIUM,
        created_by: uuid.UUID | None = None,
    ) -> AccountingMapping:
        """Create a new accounting mapping.

        Args:
            tenant_id: Tenant ID
            legal_entity_id: Optional legal entity ID
            supplier_party_id: Optional supplier party ID (NULL = any supplier)
            description_pattern: Substring/regex for line descriptions
            amount_range_min: Optional minimum amount
            amount_range_max: Optional maximum amount
            target_account_id: Target account ID
            target_tax_rule_id: Optional target tax rule ID
            target_dimension_id: Optional target dimension ID
            confidence: Confidence tier (high/medium/low)
            created_by: User ID creating the mapping

        Returns:
            Created AccountingMapping
        """
        logger.info(
            "MappingService: creating mapping for tenant %s (supplier=%s, account=%s)",
            tenant_id,
            supplier_party_id,
            target_account_id,
        )

        mapping = AccountingMapping.objects.create(
            tenant_id=tenant_id,
            legal_entity_id=legal_entity_id,
            supplier_party_id=supplier_party_id,
            description_pattern=description_pattern,
            amount_range_min=amount_range_min,
            amount_range_max=amount_range_max,
            target_account_id=target_account_id,
            target_tax_rule_id=target_tax_rule_id,
            target_dimension_id=target_dimension_id,
            confidence=confidence,
            created_by=created_by,
            is_active=True,
        )

        logger.info(
            "MappingService: mapping %s created (tenant=%s)",
            mapping.guid,
            tenant_id,
        )

        return mapping

    def update_mapping(
        self,
        mapping: AccountingMapping,
        *,
        updated_by: uuid.UUID,
        **updates: Any,
    ) -> AccountingMapping:
        """Update an existing mapping.

        Args:
            mapping: Mapping to update
            updated_by: User ID updating the mapping
            **updates: Fields to update

        Returns:
            Updated AccountingMapping

        Raises:
            ValueError: If mapping is retired
        """
        if not mapping.is_active:
            raise ValueError(
                f"Cannot update retired mapping {mapping.guid}. "
                "Create a new mapping instead."
            )

        logger.info(
            "MappingService: updating mapping %s (tenant=%s) by user %s",
            mapping.guid,
            mapping.tenant_id,
            updated_by,
        )

        for field, value in updates.items():
            setattr(mapping, field, value)

        mapping.save()

        logger.info("MappingService: mapping %s updated", mapping.guid)

        return mapping

    def retire_mapping(
        self,
        mapping: AccountingMapping,
        *,
        retired_by: uuid.UUID,
        reason: str = "",
    ) -> None:
        """Retire a mapping (soft-delete).

        Args:
            mapping: Mapping to retire
            retired_by: User ID retiring the mapping
            reason: Reason for retirement
        """
        logger.info(
            "MappingService: retiring mapping %s (tenant=%s) by user %s",
            mapping.guid,
            mapping.tenant_id,
            retired_by,
        )

        mapping.retire(retired_by, reason)

        logger.info("MappingService: mapping %s retired", mapping.guid)

    def find_mappings(
        self,
        *,
        tenant_id: uuid.UUID,
        supplier_party_id: uuid.UUID | None = None,
        description_pattern: str | None = None,
        amount: str | None = None,
        include_inactive: bool = False,
    ) -> list[AccountingMapping]:
        """Find mappings matching criteria.

        Args:
            tenant_id: Tenant ID
            supplier_party_id: Optional supplier party ID
            description_pattern: Optional description pattern to match
            amount: Optional amount to filter by range
            include_inactive: Include retired mappings

        Returns:
            List of matching AccountingMapping
        """
        logger.info(
            "MappingService: finding mappings for tenant %s (supplier=%s)",
            tenant_id,
            supplier_party_id,
        )

        queryset = AccountingMapping.objects.filter(tenant_id=tenant_id)

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        if supplier_party_id is not None:
            # Match by supplier OR "any supplier" (NULL)
            queryset = queryset.filter(
                Q(supplier_party_id=supplier_party_id)
                | Q(supplier_party_id__isnull=True)
            )

        if description_pattern:
            queryset = queryset.filter(
                description_pattern__icontains=description_pattern
            )

        if amount:
            # Filter by amount range
            queryset = queryset.filter(
                Q(amount_range_min__isnull=True) | Q(amount_range_min__lte=amount)
            ).filter(
                Q(amount_range_max__isnull=True) | Q(amount_range_max__gte=amount)
            )

        # Order by specificity: supplier-specific first, then by confidence
        queryset = queryset.order_by(
            "-supplier_party_id",  # NULL last
            "-confidence",
            "-updated_at",
        )

        mappings = list(queryset)

        logger.info(
            "MappingService: found %d mappings for tenant %s",
            len(mappings),
            tenant_id,
        )

        return mappings

    def get_mapping(self, mapping_id: uuid.UUID) -> AccountingMapping:
        """Get a mapping by ID.

        Args:
            mapping_id: Mapping ID

        Returns:
            AccountingMapping

        Raises:
            AccountingMapping.DoesNotExist: If not found
        """
        return AccountingMapping.objects.get(guid=mapping_id)

    def list_mappings(
        self,
        *,
        tenant_id: uuid.UUID,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AccountingMapping]:
        """List mappings for a tenant.

        Args:
            tenant_id: Tenant ID
            include_inactive: Include retired mappings
            limit: Max results
            offset: Offset for pagination

        Returns:
            List of AccountingMapping
        """
        queryset = AccountingMapping.objects.filter(tenant_id=tenant_id)

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return list(queryset[offset : offset + limit])
