"""Acceptance test for BR-DI-009: OCR/AI outputs never silently replace original
document or previous extraction history.

Given: A Document has undergone OCR/AI processing
When: A subsequent extraction or correction is performed
Then: The original document file in object storage is unchanged
      Previous extraction rows are unchanged (append-only)
      No silent replacement occurs
"""

import pytest
from django.test import TestCase

from apps.document_intelligence.models import Document, DocumentExtraction, ExtractionStatus
# Fixtures are provided by the sibling conftest.py in this package, auto-loaded by pytest.


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI009_NoSilentReplacement(TestCase):
    """BR-DI-009: OCR/AI outputs never silently replace original or prior extraction."""

    def test_original_document_fields_immutable(self, sample_document):
        """Original document provenance fields cannot be changed."""
        sample_document.save()

        original_key = sample_document.original_file_key
        original_hash = sample_document.content_hash
        original_filename = sample_document.original_filename
        original_size = sample_document.size_bytes

        # When: Attempt to change any immutable field
        sample_document.content_hash = "new_hash"

        # Then: ValueError is raised
        with self.assertRaises(ValueError) as ctx:
            sample_document.save()

        self.assertIn("immutable", str(ctx.exception).lower())

        # And: Original values are preserved
        reloaded = Document.objects.get(pk=sample_document.pk)
        self.assertEqual(reloaded.original_file_key, original_key)
        self.assertEqual(reloaded.content_hash, original_hash)
        self.assertEqual(reloaded.original_filename, original_filename)
        self.assertEqual(reloaded.size_bytes, original_size)

    def test_extraction_ai_fields_immutable(self, sample_document):
        """Extraction AI/OCR fields cannot be mutated after creation."""
        sample_document.save()
        extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="aws_textract",
            ocr_model_version="textract-v1",
            extraction_model_version="extract-v1",
            extraction_result={"supplier_name": "Original"},
            ai_suggestion={"account_id": "original-account"},
            confidence_score=0.85,
            confidence_evidence={"source": "mapping-123"},
            status=ExtractionStatus.COMPLETED,
        )

        # When: Attempt to change immutable AI fields
        extraction.ocr_provider = "google_document_ai"

        # Then: ValueError is raised
        with self.assertRaises(ValueError) as ctx:
            extraction.save()

        self.assertIn("BR-DI-009", str(ctx.exception))

        # And: Original AI fields are preserved
        reloaded = DocumentExtraction.objects.get(pk=extraction.pk)
        self.assertEqual(reloaded.ocr_provider, "aws_textract")
        self.assertEqual(reloaded.extraction_result["supplier_name"], "Original")
        self.assertEqual(reloaded.ai_suggestion["account_id"], "original-account")

    def test_extraction_result_immutable(self, sample_document):
        """Structured extraction result cannot be mutated."""
        sample_document.save()
        extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            extraction_result={"total_amount": "100.00"},
            status=ExtractionStatus.COMPLETED,
        )

        # When: Attempt to change extraction_result
        extraction.extraction_result = {"total_amount": "200.00"}

        # Then: ValueError is raised
        with self.assertRaises(ValueError):
            extraction.save()

        # And: Original result is preserved
        reloaded = DocumentExtraction.objects.get(pk=extraction.pk)
        self.assertEqual(reloaded.extraction_result["total_amount"], "100.00")

    def test_confidence_fields_immutable(self, sample_document):
        """Confidence score and evidence cannot be mutated."""
        from decimal import Decimal

        sample_document.save()
        extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            confidence_score=Decimal("0.90"),
            confidence_evidence={"source": "mapping-abc"},
            status=ExtractionStatus.COMPLETED,
        )

        # When: Attempt to change confidence fields
        extraction.confidence_score = Decimal("0.50")

        # Then: ValueError is raised
        with self.assertRaises(ValueError):
            extraction.save()

        # And: Original confidence is preserved
        reloaded = DocumentExtraction.objects.get(pk=extraction.pk)
        self.assertEqual(reloaded.confidence_score, Decimal("0.90"))
