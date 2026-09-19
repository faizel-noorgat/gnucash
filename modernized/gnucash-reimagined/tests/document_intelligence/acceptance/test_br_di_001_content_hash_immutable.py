"""Acceptance test for BR-DI-001: Document content hash is immutable after upload.

Given: A Document has been uploaded with a SHA-256 content_hash
When: An attempt is made to modify the content_hash field
Then: The modification MUST be rejected (ValueError or database error)
"""

import pytest
from django.test import TestCase

from apps.document_intelligence.models import Document
# Fixtures are provided by the sibling conftest.py in this package, auto-loaded by pytest.


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI001_ContentHashImmutable(TestCase):
    """BR-DI-001: Content hash is immutable after upload."""

    def test_content_hash_cannot_be_changed_after_save(self, sample_document):
        """Content hash cannot be mutated on an existing document."""
        # Given: A persisted document
        sample_document.save()
        original_hash = sample_document.content_hash

        # When: Attempt to change content_hash
        sample_document.content_hash = "different_hash_value"

        # Then: ValueError is raised (application-layer guard)
        with self.assertRaises(ValueError) as ctx:
            sample_document.save()

        self.assertIn("BR-DI-001", str(ctx.exception))
        self.assertIn("content_hash", str(ctx.exception))

        # Verify the persisted value is unchanged
        reloaded = Document.objects.get(pk=sample_document.pk)
        self.assertEqual(reloaded.content_hash, original_hash)

    def test_content_hash_computation_is_deterministic(self):
        """SHA-256 computation is pure and deterministic."""
        # Given: Same bytes
        data = b"test data for hashing"

        # When: Hash is computed twice
        hash1 = Document.compute_sha256(data)
        hash2 = Document.compute_sha256(data)

        # Then: Hashes are identical
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA-256 = 64 hex chars
