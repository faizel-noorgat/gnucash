"""Unit tests for UploadService."""

from __future__ import annotations

import uuid

import pytest
from django.test import TestCase, override_settings

from apps.document_intelligence.models import Document, DocumentSource
from apps.document_intelligence.services.storage import MockStorageClient
from apps.document_intelligence.services.upload import UploadService


@pytest.mark.django_db
class TestUploadService(TestCase):
    """Unit tests for the UploadService."""

    def setUp(self):
        self.storage_client = MockStorageClient()
        self.service = UploadService(storage_client=self.storage_client)

    @override_settings(
        DOCUMENT_INTELLIGENCE={
            "S3_BUCKET": "test-bucket",
            "OCR_PROVIDER": "mock",
        }
    )
    def test_upload_document_creates_document_with_content_hash(self):
        """Upload service computes content hash and stores document."""
        tenant_id = uuid.uuid4()
        file_bytes = b"test file content"
        expected_hash = Document.compute_sha256(file_bytes)

        document = self.service.upload_document(
            tenant_id=tenant_id,
            legal_entity_id=None,
            file_bytes=file_bytes,
            filename="test.pdf",
            mime_type="application/pdf",
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=uuid.uuid4(),
        )

        # Document is persisted
        self.assertIsNotNone(document.pk)
        self.assertEqual(document.content_hash, expected_hash)
        self.assertEqual(document.tenant_id, tenant_id)
        self.assertEqual(document.mime_type, "application/pdf")
        self.assertEqual(document.size_bytes, len(file_bytes))

    @override_settings(
        DOCUMENT_INTELLIGENCE={
            "S3_BUCKET": "test-bucket",
            "OCR_PROVIDER": "mock",
        }
    )
    def test_upload_document_stores_in_object_storage(self):
        """Upload service stores file in object storage."""
        tenant_id = uuid.uuid4()
        file_bytes = b"test file content for storage"

        document = self.service.upload_document(
            tenant_id=tenant_id,
            legal_entity_id=None,
            file_bytes=file_bytes,
            filename="test.pdf",
            mime_type="application/pdf",
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=uuid.uuid4(),
        )

        # Verify storage has the file
        stored = self.storage_client.download_file(
            bucket="test-bucket",
            key=document.original_file_key,
        )
        self.assertEqual(stored, file_bytes)

    @override_settings(
        DOCUMENT_INTELLIGENCE={
            "S3_BUCKET": "test-bucket",
            "OCR_PROVIDER": "mock",
        }
    )
    def test_upload_document_generates_s3_key(self):
        """Upload service generates S3 key with tenant/guid/filename."""
        tenant_id = uuid.uuid4()
        file_bytes = b"test"

        document = self.service.upload_document(
            tenant_id=tenant_id,
            legal_entity_id=None,
            file_bytes=file_bytes,
            filename="receipt.jpg",
            mime_type="image/jpeg",
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=uuid.uuid4(),
        )

        # Key follows pattern: tenants/{tenant_id}/documents/{guid}/{filename}
        self.assertTrue(
            document.original_file_key.startswith(f"tenants/{tenant_id}/documents/")
        )
        self.assertTrue(document.original_file_key.endswith("/receipt.jpg"))
