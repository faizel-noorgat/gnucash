"""Suggestion service — AI-generated suggestions with confidence scores.

Responsibilities:
1. Generate accounting suggestions based on extraction results
2. Trace suggestions back to explicit organizational knowledge (BR-DI-007)
3. Compute confidence scores with evidence trail (BR-DI-008)
4. Create MappingSuggestion rows (append-only audit trail)
5. NEVER auto-apply suggestions - always require human approval if low confidence

Design:
- Suggestions are derived from AccountingMapping, not LLM memory (BR-DI-007)
- Full provenance captured: source mappings, confidence, evidence (BR-DI-008)
- Low confidence routes to review queue (BR-DI-006)
- AI outputs NEVER directly post journals (BR-DI-009)
- Tenant-scoped via tenant_id (BR-DI-010)

Implements behavior-contract rules:
- BR-DI-006: low confidence routes to review queue
- BR-DI-007: suggestions trace to explicit organizational knowledge
- BR-DI-008: full provenance captured
- BR-DI-009: AI outputs never directly post journals
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol, TypedDict

from django.conf import settings
from django.db import transaction

from ..models import (
    AccountingMapping,
    Document,
    DocumentExtraction,
    MappingConfidence,
    MappingSuggestion,
)
from .extraction import ExtractionResult

logger = logging.getLogger(__name__)


class SuggestionResult(TypedDict):
    """AI suggestion result."""

    suggestion: dict
    confidence_score: float
    confidence_evidence: dict


class AISuggester(Protocol):
    """Pluggable AI suggester interface."""

    def suggest(
        self,
        *,
        tenant_id: uuid.UUID,
        extraction_result: ExtractionResult,
        document: Document,
    ) -> SuggestionResult:
        """Generate accounting suggestion.

        Args:
            tenant_id: Tenant ID
            extraction_result: Structured extraction result
            document: Source document

        Returns:
            SuggestionResult with suggestion, confidence, evidence
        """
        ...


class MockAISuggester:
    """Mock AI suggester for testing (always returns None)."""

    def suggest(
        self,
        *,
        tenant_id: uuid.UUID,
        extraction_result: ExtractionResult,
        document: Document,
    ) -> SuggestionResult:
        logger.info("MockAISuggester: generating suggestion for tenant %s", tenant_id)
        return SuggestionResult(
            suggestion={},
            confidence_score=0.0,
            confidence_evidence={"reason": "mock_suggester"},
        )


class HistoricalMappingSuggester:
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
    ) -> SuggestionResult:
        logger.info(
            "HistoricalMappingSuggester: generating suggestion for tenant %s",
            tenant_id,
        )

        supplier_name = extraction_result.get("supplier_name")
        line_items = extraction_result.get("line_items", [])

        # Look up mappings for this tenant
        mappings = AccountingMapping.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
        )

        # TODO: Filter by supplier party_id if we have it
        # This requires a party lookup service to map supplier_name -> party_id

        # If no mappings found, return low confidence
        if not mappings.exists():
            return SuggestionResult(
                suggestion={},
                confidence_score=0.0,
                confidence_evidence={"reason": "no_matching_mappings"},
            )

        # Take the first active mapping (real impl would rank by relevance)
        mapping = mappings.first()

        suggestion = {
            "account_id": str(mapping.target_account_id),
            "tax_rule_id": str(mapping.target_tax_rule_id)
            if mapping.target_tax_rule_id
            else None,
            "dimension_id": str(mapping.target_dimension_id)
            if mapping.target_dimension_id
            else None,
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
            "supplier_name": supplier_name,
            "line_item_count": len(line_items),
        }

        logger.info(
            "HistoricalMappingSuggester: suggestion generated (mapping=%s, conf=%s)",
            mapping.guid,
            confidence,
        )

        return SuggestionResult(
            suggestion=suggestion,
            confidence_score=confidence,
            confidence_evidence=evidence,
        )


class LLMSuggester:
    """LLM-based suggester using external LLM API.

    Requires LLM_API_KEY environment variable.
    Supports OpenAI, Anthropic, etc.
    """

    def __init__(self, llm_provider: str = "openai") -> None:
        self.llm_provider = llm_provider
        # TODO: Initialize LLM client

    def suggest(
        self,
        *,
        tenant_id: uuid.UUID,
        extraction_result: ExtractionResult,
        document: Document,
    ) -> SuggestionResult:
        logger.warning(
            "LLMSuggester: not yet implemented for tenant %s", tenant_id
        )
        # TODO: Implement LLM-based suggestion
        return SuggestionResult(
            suggestion={},
            confidence_score=0.0,
            confidence_evidence={"reason": "llm_suggester_not_implemented"},
        )


def get_ai_suggester() -> AISuggester:
    """Factory function to get the configured AI suggester.

    Dispatches on `settings.DOCUMENT_INTELLIGENCE` so no LLM vendor is
    hard-wired into the orchestration code. `AI_SUGGESTER` names the internal
    strategy; `AI_PROVIDER` (the documented settings key: "openai" |
    "anthropic" | "mock") selects the vendor for the LLM-backed strategy.

    Recognised `AI_SUGGESTER` values:
        "mock" (default), "historical_mapping", "llm"

    Unknown values fall back to the mock suggester with a warning rather than
    raising, matching `services.storage.get_storage_client`.

    Returns:
        AISuggester instance. Suggestions only ever *propose* accounting
        entries — they are never posted directly (BR-DI-009).
    """
    conf = settings.DOCUMENT_INTELLIGENCE

    if not conf.get("AI_SUGGESTIONS_ENABLED", True):
        return MockAISuggester()

    suggester_name = conf.get("AI_SUGGESTER") or conf.get("AI_PROVIDER") or "mock"

    if suggester_name == "mock":
        return MockAISuggester()
    elif suggester_name == "historical_mapping":
        return HistoricalMappingSuggester()
    elif suggester_name in ("llm", "openai", "anthropic"):
        llm_provider = (
            conf.get("LLM_PROVIDER", "openai")
            if suggester_name == "llm"
            else suggester_name
        )
        return LLMSuggester(llm_provider=llm_provider)
    else:
        logger.warning(
            "Unknown AI suggester '%s', falling back to mock", suggester_name
        )
        return MockAISuggester()


class SuggestionService:
    """Orchestrates AI suggestion generation.

    Usage:
        service = SuggestionService()
        suggestion = service.generate_suggestion(extraction)
    """

    def __init__(self, suggester: AISuggester | None = None) -> None:
        """Initialize suggestion service.

        Args:
            suggester: AI suggester to use. If None, uses configured default.
        """
        self.conf = settings.DOCUMENT_INTELLIGENCE
        self.suggester = suggester or self._get_default_suggester()

    def _get_default_suggester(self) -> AISuggester:
        """Get default AI suggester from settings (see the factory)."""
        return get_ai_suggester()

    def generate_suggestion(
        self,
        extraction: DocumentExtraction,
    ) -> MappingSuggestion:
        """Generate AI suggestion for an extraction.

        Creates a MappingSuggestion row with full provenance (BR-DI-008).
        If confidence < threshold, routes to review queue (BR-DI-006).

        Args:
            extraction: Extraction to generate suggestion for

        Returns:
            Created MappingSuggestion
        """
        document = extraction.document
        extraction_result = extraction.extraction_result

        logger.info(
            "SuggestionService: generating suggestion for extraction %s (tenant=%s)",
            extraction.guid,
            document.tenant_id,
        )

        # Generate suggestion
        result = self.suggester.suggest(
            tenant_id=document.tenant_id,
            extraction_result=extraction_result,
            document=document,
        )

        # Create MappingSuggestion
        suggestion = MappingSuggestion.objects.create(
            tenant_id=document.tenant_id,
            extraction=extraction,
            suggested_account_id=result["suggestion"].get("account_id"),
            suggested_tax_rule_id=result["suggestion"].get("tax_rule_id"),
            suggested_dimension_id=result["suggestion"].get("dimension_id"),
            suggested_party_id=result["suggestion"].get("party_id"),
            source_mapping_ids=result["confidence_evidence"].get(
                "source_mapping_ids", []
            ),
            confidence_score=result["confidence_score"],
            evidence=result["confidence_evidence"],
            llm_provider=self.conf.get("LLM_PROVIDER", "unknown"),
            llm_model_version=self.conf.get("LLM_MODEL_VERSION", "unknown"),
        )

        logger.info(
            "SuggestionService: suggestion %s created (conf=%s)",
            suggestion.guid,
            suggestion.confidence_score,
        )

        # Route to review queue if low confidence (BR-DI-006)
        threshold = self.conf.get("AI_CONFIDENCE_THRESHOLD", 0.80)
        if result["confidence_score"] < threshold:
            from ..models import ReviewQueue, ReviewStatus

            ReviewQueue.objects.create(
                tenant_id=document.tenant_id,
                document=document,
                extraction=extraction,
                suggestion=suggestion,
                status=ReviewStatus.OPEN,
                priority=int((threshold - result["confidence_score"]) * 100),
                reason="low_confidence",
            )
            logger.info(
                "SuggestionService: suggestion %s routed to review queue (conf=%s < threshold=%s)",
                suggestion.guid,
                result["confidence_score"],
                threshold,
            )

        return suggestion

    def accept_suggestion(
        self,
        suggestion: MappingSuggestion,
        user_id: uuid.UUID | None,
    ) -> None:
        """Accept a suggestion.

        Args:
            suggestion: Suggestion to accept
            user_id: User ID accepting the suggestion
        """
        logger.info(
            "SuggestionService: accepting suggestion %s by user %s",
            suggestion.guid,
            user_id,
        )
        suggestion.accept(user_id)

    def reject_suggestion(
        self,
        suggestion: MappingSuggestion,
        user_id: uuid.UUID | None,
    ) -> None:
        """Reject a suggestion.

        Args:
            suggestion: Suggestion to reject
            user_id: User ID rejecting the suggestion
        """
        logger.info(
            "SuggestionService: rejecting suggestion %s by user %s",
            suggestion.guid,
            user_id,
        )
        suggestion.reject(user_id)
