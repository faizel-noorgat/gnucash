"""Acceptance test for BR-DI-004: Human corrections create new extraction version.

Given: A DocumentExtraction has been created by OCR/AI
When: A human reviewer corrects the extraction
Then: A NEW DocumentExtraction row is created with version+1 and is_human_correction=True
      The original extraction row is NOT modified (only reviewed_by/reviewed_at are set)
"""

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.document_intelligence.models import (
    Document,
    DocumentExtraction,
    ExtractionStatus,
)
from apps.document_intelligence.services.extraction import ExtractionService
# Fixtures are provided by the sibling conftest.py in this package, auto-loaded by pytest.


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI004_HumanCorrectionCreatesNewVersion(TestCase):
    """BR-DI-004: Human corrections create new extraction version (never modify old)."""

    def test_human_correction_creates_new_version(self, sample_document, user_id):
        """Human correction creates v+1, does not mutate original."""
        # Given: A persisted document with an extraction
        sample_document.save()
        original_extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            extraction_result={"supplier_name": "Original Supplier", "total_amount": "100.00"},
            status=ExtractionStatus.COMPLETED,
        )

        # When: Human correction is applied
        from apps.document_intelligence.services.ocr import get_ocr_provider
        from apps.document_intelligence.services.extraction import get_extraction_engine
        from apps.document_intelligence.services.suggestion import get_ai_suggester

        service = ExtractionService(
            ocr_provider=get_ocr_provider(),
            extraction_engine=get_extraction_engine(),
            ai_suggester=get_ai_suggester(),
        )

        correction = {"supplier_name": "Corrected Supplier", "total_amount": "150.00"}
        new_extraction = service.apply_human_correction(
            extraction=original_extraction,
            correction=correction,
            reviewer_id=user_id,
            note="Fixed supplier name and amount",
        )

        # Then: New extraction has version=2
        self.assertEqual(new_extraction.version, 2)

        # And: New extraction is marked as human correction
        self.assertTrue(new_extraction.is_human_correction)

        # And: New extraction has the correction
        self.assertEqual(new_extraction.human_correction["supplier_name"], "Corrected Supplier")
        self.assertEqual(new_extraction.human_correction["total_amount"], "150.00")

        # And: Original extraction is unchanged (only reviewed_by/at are set)
        reloaded_original = DocumentExtraction.objects.get(pk=original_extraction.pk)
        self.assertEqual(
            reloaded_original.extraction_result["supplier_name"], "Original Supplier"
        )
        self.assertEqual(reloaded_original.extraction_result["total_amount"], "100.00")
        self.assertIsNone(reloaded_original.human_correction)
        self.assertEqual(reloaded_original.reviewed_by, user_id)
        self.assertIsNotNone(reloaded_original.reviewed_at)

    def test_original_extraction_fields_immutable_after_review(
        self, sample_document, user_id
    ):
        """Original extraction's OCR/AI fields cannot be mutated during review."""
        sample_document.save()
        extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            extraction_result={"supplier_name": "Supplier A"},
            ai_suggestion={"account_id": "acc-123"},
            confidence_score=0.85,
            status=ExtractionStatus.COMPLETED,
        )

        # When: Attempt to mutate immutable fields
        extraction.ocr_provider = "different_provider"

        # Then: ValueError is raised
        with self.assertRaises(ValueError) as ctx:
            extraction.save()

        self.assertIn("BR-DI-003", str(ctx.exception))
        self.assertIn("ocr_provider", str(ctx.exception))
