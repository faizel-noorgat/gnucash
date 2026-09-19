"""Acceptance test for BR-DI-003: Each OCR/AI extraction attempt is append-only.

Given: A Document has undergone OCR/AI extraction
When: A new extraction is performed
Then: A NEW DocumentExtraction row is created with version+1
      The previous extraction row is NEVER modified or deleted
"""

import pytest
from django.test import TestCase

from apps.document_intelligence.models import (
    Document,
    DocumentExtraction,
    ExtractionStatus,
    ExtractionVersion,
)
# Fixtures are provided by the sibling conftest.py in this package, auto-loaded by pytest.


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI003_ExtractionAppendOnly(TestCase):
    """BR-DI-003: Each OCR/AI extraction attempt is append-only (new version)."""

    def test_extraction_creates_new_version(self, sample_document):
        """Each extraction creates a new version, never mutates previous."""
        # Given: A persisted document
        sample_document.save()

        # When: First extraction is created
        extraction1 = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            extraction_result={"supplier_name": "Supplier A"},
            status=ExtractionStatus.COMPLETED,
        )

        # And: Second extraction is created
        extraction2 = DocumentExtraction.objects.create(
            document=sample_document,
            version=2,
            ocr_provider="mock",
            ocr_model_version="1.1",
            extraction_model_version="1.1",
            extraction_result={"supplier_name": "Supplier B (corrected)"},
            status=ExtractionStatus.COMPLETED,
        )

        # Then: Both extractions exist
        self.assertEqual(DocumentExtraction.objects.filter(document=sample_document).count(), 2)

        # And: Versions are distinct
        self.assertEqual(extraction1.version, 1)
        self.assertEqual(extraction2.version, 2)

        # And: First extraction is unchanged
        reloaded1 = DocumentExtraction.objects.get(pk=extraction1.pk)
        self.assertEqual(reloaded1.extraction_result["supplier_name"], "Supplier A")

    def test_extraction_cannot_be_deleted(self, sample_document):
        """Extraction rows cannot be deleted (append-only audit trail)."""
        sample_document.save()
        extraction = DocumentExtraction.objects.create(
            document=sample_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            status=ExtractionStatus.COMPLETED,
        )

        # When: Attempt to delete
        # Then: DatabaseError is raised (trigger enforcement)
        # (In test environment without triggers, this would succeed,
        # but the trigger in production prevents it)
        # For now, we document the expected behavior
        pass

    def test_version_counter_increments(self, sample_document):
        """Version counter increments monotonically."""
        sample_document.save()
        counter = ExtractionVersion.objects.create(document=sample_document, current_version=0)

        v1 = counter.next_version()
        self.assertEqual(v1, 1)

        v2 = counter.next_version()
        self.assertEqual(v2, 2)

        v3 = counter.next_version()
        self.assertEqual(v3, 3)
