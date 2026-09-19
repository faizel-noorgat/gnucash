"""Accounting mappings — explicit organizational knowledge.

BR-DI-007: Accounting mappings MUST be explicit organizational knowledge,
NOT stored inside the LLM's parameters / memory. Every suggestion the AI
produces must trace back to a stored AccountingMapping (or a MappingSuggestion
derived from one) that a human has authored or approved.

A mapping says: "for this tenant, when the supplier is X and the line
description looks like Y, use account A, tax rule T, dimension D."
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class MappingConfidence(models.TextChoices):
    """Human-assigned confidence tier for a mapping.

    Used together with the AI's numerical confidence_score to decide whether
    a suggestion auto-approves or routes to the review queue (BR-DI-006).
    """

    HIGH = "high", "High — auto-apply"
    MEDIUM = "medium", "Medium — suggest with confirmation"
    LOW = "low", "Low — always require review"


class AccountingMapping(models.Model):
    """An explicit organizational accounting rule.

    Examples:
      - supplier='Staples' + description_like='printer paper' ->
        account='Office Supplies Expense', tax='GST Input'
      - any supplier + description_like='monthly hosting' ->
        account='Cloud Infrastructure', dimension='Engineering'
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    legal_entity_id = models.UUIDField(null=True, blank=True, db_index=True)

    # --- Trigger conditions -------------------------------------------------
    supplier_party_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Match by supplier party. NULL means 'any supplier'.",
    )
    description_pattern = models.CharField(
        max_length=255,
        blank=True,
        help_text="Substring / regex matched against line descriptions.",
    )
    amount_range_min = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
    )
    amount_range_max = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
    )

    # --- Target -------------------------------------------------------------
    target_account_id = models.UUIDField(db_index=True)
    target_tax_rule_id = models.UUIDField(null=True, blank=True)
    target_dimension_id = models.UUIDField(null=True, blank=True)

    # --- Governance ---------------------------------------------------------
    confidence = models.CharField(
        max_length=16,
        choices=MappingConfidence.choices,
        default=MappingConfidence.MEDIUM,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.UUIDField(null=True, blank=True)
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    retired_by = models.UUIDField(null=True, blank=True)
    retirement_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "document_intelligence"
        db_table = "accounting_mappings"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "supplier_party_id"]),
            models.Index(fields=["tenant_id", "is_active"]),
        ]

    def retire(self, user_id: uuid.UUID | None, reason: str = "") -> None:
        """Retire this mapping (soft-delete)."""
        self.is_active = False
        self.retired_at = timezone.now()
        self.retired_by = user_id
        self.retirement_reason = reason
        self.save()

    def __str__(self) -> str:
        return f"Mapping {self.guid} (tenant={self.tenant_id})"
