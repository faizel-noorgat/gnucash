"""Acceptance test for BR-DI-002: Original object-storage file is immutable after upload.

Given: A Document has been uploaded to object storage with a specific S3 key
When: An attempt is made to modify the original_file_key field
Then: The modification MUST be rejected (ValueError or database error)
"""

import pytest
from django.test import TestCase

from document_intelligence.models import Document
from document_intelligence.tests.conftest import *  # noqa: F401, F403


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI002_ObjectStorageImmutable(TestCase):
    """BR-DI-002: Original object-storage reference is immutable after upload."""

    def test_original_file_key_cannot_be_changed(self, sample_document):
        """Original file key cannot be mutated on an existing document."""
        # Given: A persisted document
        sample_document.save()
        original_key = sample_document.original_file_key

        # When: Attempt to change original_file_key
        sample_document.original_file_key = "different/key.pdf"

        # Then: ValueError is raised
        with self.assertRaises(ValueError) as ctx:
            sample_document.save()

        self.assertIn("BR-DI-001", str(ctx.exception))  # or BR-DI-002
        self.assertIn("original_file_key", str(ctx.exception))

        # Verify persisted value is unchanged
        reloaded = Document.objects.get(pk=sample_document.pk)
        self.assertEqual(reloaded.original_file_key, original_key)

    def test_uploaded_at_cannot_be_changed(self, sample_document):
        """Upload timestamp cannot be mutated."""
        sample_document.save()
        original_ts = sample_document.uploaded_at

        from django.utils import timezone

        sample_document.uploaded_at = timezone.now()

        with self.assertRaises(ValueError):
            sample_document.save()

        reloaded = Document.objects.get(pk=sample_document.pk)
        self.assertEqual(reloaded.uploaded_at, original_ts)

    def test_tenant_id_cannot_be_changed(self, sample_document, tenant_id):
        """Tenant ID cannot be mutated (RLS isolation)."""
        sample_document.save()

        import uuid

        sample_document.tenant_id = uuid.uuid4()

        with self.assertRaises(ValueError) as ctx:
            sample_document.save()

        self.assertIn("tenant_id", str(ctx.exception))

        reloaded = Document.objects.get(pk=sample_document.pk)
        self.assertEqual(reloaded.tenant_id, tenant_id)
