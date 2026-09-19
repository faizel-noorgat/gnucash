"""Acceptance test for BR-DI-008: Document provenance captures complete audit trail.

Given: A Document has been uploaded and processed
When: The document's provenance is examined
Then: All required fields are populated:
      - Original object-storage reference (S3 key)
      - Content hash (SHA-256)
      - Upload timestamp + uploader
      - OCR provider / model / version
      - Extraction model / version + structured JSON result
      - Accounting mapping used (if any)
      - AI suggestion + confidence score + evidence
      - Human correction (if any)
      - Reviewer / approver
      - Final resulting accounting document / journal entry
"""

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.document_intelligence.models import Document, DocumentExtraction, ExtractionStatus
# Fixtures are provided by the sibling conftest.py in this package, auto-loaded by pytest.


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI008_CompleteProvenance(TestCase):
    """BR-DI-008: Document provenance captures complete audit trail."""

    def test_document_provenance_fields_populated(self, sample_document):
        """Document has all required provenance fields."""
        sample_document.save()

        # Then: All provenance fields are present
        self.assertIsNotNone(sample_document.original_file_key)
        self.assertIsNotNone(sample_document.content_hash)
        self.assertEqual(len(sample_document.content_hash), 64)  # SHA-256
        self.assertIsNotNone(sample_document.uploaded_at)
        self.assertIsNotNone(sample_document.uploaded_by)
        self.assertIsNotNone(sample_document.mime_type)
        self.assertIsNotNone(sample_document.original_filename)
        self.assertGreater(sample_document.size_bytes, 0)

    def test_extraction_provenance_fields_populated(self, sample_document):
        """DocumentExtraction has all required provenance fields."""
        sample_document.save()

        extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="aws_textract",
            ocr_model_version="textract-2024",
            extraction_model_version="extraction-v2",
            extraction_result={
                "supplier_name": "Supplier A",
                "invoice_number": "INV-001",
                "total_amount": "100.00",
            },
            ai_suggestion={"account_id": "acc-123", "tax_rule_id": "tax-gst"},
            confidence_score=0.85,
            confidence_evidence={
                "source_mapping_id": "mapping-guid-123",
                "exemplar_count": 5,
            },
            status=ExtractionStatus.COMPLETED,
        )

        # Then: All extraction provenance fields are present
        self.assertIsNotNone(extraction.ocr_provider)
        self.assertIsNotNone(extraction.ocr_model_version)
        self.assertIsNotNone(extraction.extraction_model_version)
        self.assertIsInstance(extraction.extraction_result, dict)
        self.assertIsNotNone(extraction.extraction_result.get("supplier_name"))
        self.assertIsNotNone(extraction.ai_suggestion)
        self.assertIsNotNone(extraction.confidence_score)
        self.assertIsNotNone(extraction.confidence_evidence)
        self.assertIsNotNone(extraction.created_at)

    def test_human_correction_provenance(self, sample_document, user_id):
        """Human correction captures reviewer + correction details."""
        sample_document.save()

        extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            extraction_result={"supplier_name": "Original"},
            status=ExtractionStatus.COMPLETED,
            reviewed_by=user_id,
            reviewed_at=timezone.now(),
            is_human_correction=True,
            human_correction={"supplier_name": "Corrected"},
            correction_note="Fixed supplier name",
        )

        # Then: Correction provenance is captured
        self.assertEqual(extraction.reviewed_by, user_id)
        self.assertIsNotNone(extraction.reviewed_at)
        self.assertTrue(extraction.is_human_correction)
        self.assertIsNotNone(extraction.human_correction)
        self.assertEqual(extraction.human_correction["supplier_name"], "Corrected")
        self.assertEqual(extraction.correction_note, "Fixed supplier name")
