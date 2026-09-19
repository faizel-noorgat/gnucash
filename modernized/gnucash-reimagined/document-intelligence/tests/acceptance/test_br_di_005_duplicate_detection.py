"""Acceptance test for BR-DI-005: Duplicate detection identifies documents with same
invoice number + supplier + amount within a date window.

Given: A Document has been uploaded
When: A second Document with the same content hash (or semantic duplicate) is uploaded
Then: The second document is flagged as is_duplicate=True
      And linked to the original via duplicate_of
"""

import pytest
from django.test import TestCase

from document_intelligence.models import Document, DocumentSource
from document_intelligence.services.duplicate import DuplicateDetectionService
from document_intelligence.tests.conftest import *  # noqa: F401, F403


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI005_DuplicateDetection(TestCase):
    """BR-DI-005: Duplicate detection based on content hash / semantic match."""

    def test_content_hash_duplicate_detected(self, tenant_id, user_id):
        """Exact byte-for-byte duplicate is detected via content hash."""
        # Given: Two documents with identical content
        file_bytes = b"identical content for both documents"
        content_hash = Document.compute_sha256(file_bytes)

        doc1 = Document.objects.create(
            tenant_id=tenant_id,
            original_file_key=f"key1/{content_hash}",
            content_hash=content_hash,
            mime_type="application/pdf",
            original_filename="doc1.pdf",
            size_bytes=len(file_bytes),
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )

        doc2 = Document(
            tenant_id=tenant_id,
            original_file_key=f"key2/{content_hash}",
            content_hash=content_hash,  # Same hash
            mime_type="application/pdf",
            original_filename="doc2.pdf",
            size_bytes=len(file_bytes),
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )

        # When: Duplicate detection runs
        service = DuplicateDetectionService()
        is_dup = service.detect_and_mark(doc2)

        # Then: Duplicate is detected
        self.assertTrue(is_dup)
        self.assertTrue(doc2.is_duplicate)
        self.assertEqual(doc2.duplicate_of, doc1)

    def test_different_content_not_flagged_as_duplicate(
        self, tenant_id, user_id
    ):
        """Documents with different content are not flagged as duplicates."""
        # Given: Two documents with different content
        doc1 = Document.objects.create(
            tenant_id=tenant_id,
            original_file_key="key1",
            content_hash=Document.compute_sha256(b"content A"),
            mime_type="application/pdf",
            original_filename="doc1.pdf",
            size_bytes=9,
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )

        doc2 = Document(
            tenant_id=tenant_id,
            original_file_key="key2",
            content_hash=Document.compute_sha256(b"content B"),  # Different hash
            mime_type="application/pdf",
            original_filename="doc2.pdf",
            size_bytes=9,
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )

        # When: Duplicate detection runs
        service = DuplicateDetectionService()
        is_dup = service.detect_and_mark(doc2)

        # Then: Not flagged as duplicate
        self.assertFalse(is_dup)
        self.assertFalse(doc2.is_duplicate)
        self.assertIsNone(doc2.duplicate_of)

    def test_duplicate_detection_is_tenant_scoped(self, user_id):
        """Duplicate detection only considers documents within the same tenant."""
        import uuid

        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        content = b"same content across tenants"
        content_hash = Document.compute_sha256(content)

        # Given: Same content in different tenants
        Document.objects.create(
            tenant_id=tenant_a,
            original_file_key="key_a",
            content_hash=content_hash,
            mime_type="application/pdf",
            original_filename="doc_a.pdf",
            size_bytes=len(content),
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )

        doc_b = Document(
            tenant_id=tenant_b,
            original_file_key="key_b",
            content_hash=content_hash,
            mime_type="application/pdf",
            original_filename="doc_b.pdf",
            size_bytes=len(content),
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )

        # When: Duplicate detection runs for tenant_b document
        service = DuplicateDetectionService()
        is_dup = service.detect_and_mark(doc_b)

        # Then: NOT flagged as duplicate (different tenant)
        self.assertFalse(is_dup)
        self.assertFalse(doc_b.is_duplicate)
