"""Mapping suggestion model — AI-generated accounting suggestions.

BR-DI-007: Every AI suggestion must trace back to explicit organizational
knowledge (AccountingMapping) and preserve the evidence trail.

MappingSuggestion is stored separately from AccountingMapping so that:
  - We keep the evidence trail (BR-DI-008)
  - Humans can approve / reject / modify without mutating the original mapping
  - The approved suggestion becomes the basis of a NEW AccountingMapping
    if the user chooses to "learn" from the correction
"""

from __future__ import annotations

import uuid

from django.db import models


class MappingSuggestion(models.Model):
    """An AI-generated suggestion, derived from one or more AccountingMappings.

    Lifecycle:
    1. Created by AI suggestion pipeline with confidence_score and evidence
    2. If confidence < threshold, routed to ReviewQueue (BR-DI-006)
    3. Human reviewer can accept, reject, or correct
    4. If accepted, may trigger creation of new AccountingMapping (learning)
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    extraction = models.ForeignKey(
        "document_intelligence.DocumentExtraction",
        on_delete=models.CASCADE,
        related_name="mapping_suggestions",
    )

    # --- What was suggested -------------------------------------------------
    suggested_account_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Suggested target account for the journal entry.",
    )
    suggested_tax_rule_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Suggested tax rule.",
    )
    suggested_dimension_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Suggested dimension (e.g., department, project).",
    )
    suggested_party_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Suggested party (supplier or customer).",
    )

    # --- Provenance (BR-DI-008) ---------------------------------------------
    source_mapping_ids = models.JSONField(
        default=list,
        help_text="List of AccountingMapping.guid that contributed to this suggestion.",
    )
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="0.0000 – 1.0000. Used for review routing (BR-DI-006).",
    )
    evidence = models.JSONField(
        default=dict,
        help_text="Provenance trail: exemplar IDs, weights, which mappings matched.",
    )

    # --- AI/LLM provenance --------------------------------------------------
    llm_provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. openai, anthropic, or 'rule_based' if no LLM used.",
    )
    llm_model_version = models.CharField(
        max_length=100,
        blank=True,
        help_text="Model version used for suggestion.",
    )

    # --- Lifecycle ----------------------------------------------------------
    accepted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if human accepted this suggestion.",
    )
    rejected = models.BooleanField(
        default=False,
        help_text="True if human rejected this suggestion.",
    )
    decided_by = models.UUIDField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "document_intelligence"
        db_table = "mapping_suggestions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "accepted"]),
            models.Index(fields=["extraction", "confidence_score"]),
        ]

    def accept(self, user_id: uuid.UUID | None) -> None:
        """Mark this suggestion as accepted."""
        from django.utils import timezone

        self.accepted = True
        self.rejected = False
        self.decided_by = user_id
        self.decided_at = timezone.now()
        self.save(update_fields=["accepted", "rejected", "decided_by", "decided_at"])

    def reject(self, user_id: uuid.UUID | None) -> None:
        """Mark this suggestion as rejected."""
        from django.utils import timezone

        self.accepted = False
        self.rejected = True
        self.decided_by = user_id
        self.decided_at = timezone.now()
        self.save(update_fields=["accepted", "rejected", "decided_by", "decided_at"])

    def __str__(self) -> str:
        return f"Suggestion {self.guid} (conf={self.confidence_score})"
