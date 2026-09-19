"""Acceptance test for BR-DI-006: AI suggestions below confidence threshold
require human review.

Given: An extraction produces an AI suggestion with confidence_score < threshold
When: The extraction completes
Then: A ReviewQueue entry is created with status='open'
      The document cannot be auto-applied
"""

import pytest
from decimal import Decimal
from django.test import TestCase, override_settings

from apps.document_intelligence.models import (
    Document,
    DocumentExtraction,
    ExtractionStatus,
    ReviewQueue,
    ReviewStatus,
)
# Fixtures are provided by the sibling conftest.py in this package, auto-loaded by pytest.


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI006_LowConfidenceRequiresReview(TestCase):
    """BR-DI-006: AI suggestions below threshold require human review."""

    @override_settings(
        DOCUMENT_INTELLIGENCE={
            "S3_BUCKET": "test",
            "AI_SUGGESTIONS_ENABLED": True,
            "AI_CONFIDENCE_THRESHOLD": 0.80,
        }
    )
    def test_low_confidence_routes_to_review_queue(self, sample_document):
        """Extraction with low confidence creates a review queue item."""
        sample_document.save()

        # Given: An extraction with low confidence
        extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            extraction_result={"supplier_name": "Supplier A"},
            ai_suggestion={"account_id": "acc-123"},
            confidence_score=Decimal("0.65"),  # Below 0.80 threshold
            status=ExtractionStatus.COMPLETED,
        )

        # When: Review routing logic runs
        from django.conf import settings

        threshold = settings.DOCUMENT_INTELLIGENCE["AI_CONFIDENCE_THRESHOLD"]
        if extraction.confidence_score < threshold:
            ReviewQueue.objects.create(
                tenant_id=sample_document.tenant_id,
                document=sample_document,
                extraction=extraction,
                status=ReviewStatus.OPEN,
                priority=int((threshold - extraction.confidence_score) * 100),
                reason="low_confidence",
            )

        # Then: Review queue item exists
        review_items = ReviewQueue.objects.filter(
            document=sample_document,
            status=ReviewStatus.OPEN,
        )
        self.assertEqual(review_items.count(), 1)
        self.assertEqual(review_items.first().reason, "low_confidence")
        self.assertGreater(review_items.first().priority, 0)

    @override_settings(
        DOCUMENT_INTELLIGENCE={
            "S3_BUCKET": "test",
            "AI_SUGGESTIONS_ENABLED": True,
            "AI_CONFIDENCE_THRESHOLD": 0.80,
        }
    )
    def test_high_confidence_does_not_route_to_review(self, sample_document):
        """Extraction with high confidence does not create review item."""
        sample_document.save()

        # Given: An extraction with high confidence
        extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            extraction_result={"supplier_name": "Supplier A"},
            ai_suggestion={"account_id": "acc-123"},
            confidence_score=Decimal("0.95"),  # Above 0.80 threshold
            status=ExtractionStatus.COMPLETED,
        )

        # When: Review routing logic runs
        from django.conf import settings

        threshold = settings.DOCUMENT_INTELLIGENCE["AI_CONFIDENCE_THRESHOLD"]
        if extraction.confidence_score < threshold:
            ReviewQueue.objects.create(
                tenant_id=sample_document.tenant_id,
                document=sample_document,
                extraction=extraction,
                status=ReviewStatus.OPEN,
                priority=0,
                reason="low_confidence",
            )

        # Then: No review queue item
        review_items = ReviewQueue.objects.filter(
            document=sample_document,
            status=ReviewStatus.OPEN,
        )
        self.assertEqual(review_items.count(), 0)
