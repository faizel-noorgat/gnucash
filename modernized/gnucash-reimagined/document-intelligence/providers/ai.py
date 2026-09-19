"""AI suggester interface and factory.

Generates accounting suggestions (account, tax, dimension, party) based on
extraction results and historical AccountingMappings.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Protocol

from django.conf import settings

from ..models import Document
from .extraction import ExtractionResult


class AISuggester(Protocol):
    """AI suggester interface."""

    def suggest(
        self,
        *,
        tenant_id: uuid.UUID,
        extraction_result: ExtractionResult,
        document: Document,
    ) -> tuple[dict, float, dict]:
        """Return (suggestion_dict, confidence_score, evidence_dict)."""
        ...


class BaseAISuggester(ABC):
    """Base class for AI suggesters."""

    @abstractmethod
    def suggest(
        self,
        *,
        tenant_id: uuid.UUID,
        extraction_result: ExtractionResult,
        document: Document,
    ) -> tuple[dict, float, dict]:
        pass


class MockAISuggester(BaseAISuggester):
    """Mock AI suggester for testing (always returns None)."""

    def suggest(
        self,
        *,
        tenant_id: uuid.UUID,
        extraction_result: ExtractionResult,
        document: Document,
    ) -> tuple[dict, float, dict]:
        return {}, 0.0, {}


class HistoricalMappingSuggester(BaseAISuggester):
    """Suggests based on historical AccountingMappings.

    This is BR-DI-007: explicit organizational knowledge, NOT LLM memory.
    The suggester looks up mappings that match the supplier + description
    pattern and returns the most frequent / highest-confidence mapping.
    """

    def suggest(
        self,
        *,
        tenant_id: uuid.UUID,
        extraction_result: ExtractionResult,
        document: Document,
    ) -> tuple[dict, float, dict]:
        from ..models import AccountingMapping, MappingConfidence

        supplier_name = extraction_result.get("supplier_name")
        line_items = extraction_result.get("line_items", [])

        # Look up mappings for this tenant + supplier
        mappings = AccountingMapping.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
        )

        if supplier_name:
            # Filter by supplier (if we have party_id lookup)
            # For now, skip this since we don't have party_id yet
            pass

        # If no mappings found, return low confidence
        if not mappings.exists():
            return {}, 0.0, {"reason": "no_matching_mappings"}

        # Take the first active mapping (real impl would rank by relevance)
        mapping = mappings.first()

        suggestion = {
            "account_id": str(mapping.target_account_id),
            "tax_rule_id": str(mapping.target_tax_rule_id) if mapping.target_tax_rule_id else None,
            "dimension_id": str(mapping.target_dimension_id) if mapping.target_dimension_id else None,
        }

        # Confidence based on mapping's confidence tier
        confidence_map = {
            MappingConfidence.HIGH: 0.95,
            MappingConfidence.MEDIUM: 0.75,
            MappingConfidence.LOW: 0.50,
        }
        confidence = confidence_map.get(mapping.confidence, 0.50)

        evidence = {
            "source_mapping_id": str(mapping.guid),
            "mapping_confidence_tier": mapping.confidence,
        }

        return suggestion, confidence, evidence


def get_ai_suggester() -> BaseAISuggester | None:
    """Factory function to get the configured AI suggester.

    Returns None if AI suggestions are disabled.
    """
    if not settings.DOCUMENT_INTELLIGENCE.get("AI_SUGGESTIONS_ENABLED", True):
        return None

    suggester_name = settings.DOCUMENT_INTELLIGENCE.get("AI_SUGGESTER", "mock")

    if suggester_name == "mock":
        return MockAISuggester()
    elif suggester_name == "historical_mapping":
        return HistoricalMappingSuggester()
    else:
        raise ValueError(f"Unknown AI suggester: {suggester_name}")
