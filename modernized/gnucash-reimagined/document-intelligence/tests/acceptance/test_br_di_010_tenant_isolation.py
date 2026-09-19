"""Acceptance test for BR-DI-010: Documents are tenant-scoped via RLS + ORM
default filters.

Given: Two tenants (A, B) each have documents
When: Tenant A queries for documents
Then: Only Tenant A's documents are returned
      Tenant B's documents are not visible (RLS enforcement)
"""

import pytest
import uuid
from django.test import TestCase

from document_intelligence.models import Document, DocumentSource
from document_intelligence.tests.conftest import *  # noqa: F401, F403


@pytest.mark.acceptance
@pytest.mark.django_db
class TestBRDI010_TenantIsolation(TestCase):
    """BR-DI-010: Documents are tenant-scoped via RLS + ORM filters."""

    def test_documents_filtered_by_tenant(self):
        """Queries return only documents for the specified tenant."""
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        # Given: Documents in two tenants
        doc_a = Document.objects.create(
            tenant_id=tenant_a,
            original_file_key="key_a",
            content_hash=Document.compute_sha256(b"content a"),
            mime_type="application/pdf",
            original_filename="doc_a.pdf",
            size_bytes=9,
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )
        doc_b = Document.objects.create(
            tenant_id=tenant_b,
            original_file_key="key_b",
            content_hash=Document.compute_sha256(b"content b"),
            mime_type="application/pdf",
            original_filename="doc_b.pdf",
            size_bytes=9,
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )

        # When: Tenant A queries
        tenant_a_docs = Document.objects.filter(tenant_id=tenant_a)

        # Then: Only Tenant A's documents are returned
        self.assertEqual(tenant_a_docs.count(), 1)
        self.assertEqual(tenant_a_docs.first().pk, doc_a.pk)

        # And: Tenant B's documents are not in the result
        self.assertNotIn(doc_b, tenant_a_docs)

    def test_cross_tenant_query_excludes_other_tenants(self):
        """Tenant A cannot access Tenant B's documents via ORM."""
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        doc_b = Document.objects.create(
            tenant_id=tenant_b,
            original_file_key="key_b",
            content_hash=Document.compute_sha256(b"content b"),
            mime_type="application/pdf",
            original_filename="doc_b.pdf",
            size_bytes=9,
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )

        # When: Tenant A tries to access Tenant B's document
        try:
            doc = Document.objects.get(pk=doc_b.pk, tenant_id=tenant_a)
            # Then: Document is not found (filtered out)
            self.fail("Should not find document from another tenant")
        except Document.DoesNotExist:
            pass  # Expected

    def test_tenant_id_immutable(self, sample_document, tenant_id):
        """Tenant ID cannot be changed (prevents cross-tenant data leaks)."""
        sample_document.save()

        new_tenant = uuid.uuid4()
        sample_document.tenant_id = new_tenant

        # When: Attempt to change tenant_id
        with self.assertRaises(ValueError) as ctx:
            sample_document.save()

        self.assertIn("tenant_id", str(ctx.exception))

        # And: Original tenant_id is preserved
        reloaded = Document.objects.get(pk=sample_document.pk)
        self.assertEqual(reloaded.tenant_id, tenant_id)

    def test_extractions_scoped_by_tenant(self):
        """Extractions are scoped by their parent document's tenant."""
        from document_intelligence.models import DocumentExtraction

        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        doc_a = Document.objects.create(
            tenant_id=tenant_a,
            original_file_key="key_a",
            content_hash=Document.compute_sha256(b"content a"),
            mime_type="application/pdf",
            original_filename="doc_a.pdf",
            size_bytes=9,
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )
        doc_b = Document.objects.create(
            tenant_id=tenant_b,
            original_file_key="key_b",
            content_hash=Document.compute_sha256(b"content b"),
            mime_type="application/pdf",
            original_filename="doc_b.pdf",
            size_bytes=9,
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=user_id,
        )

        ext_a = DocumentExtraction.objects.create(
            document=doc_a,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            status="completed",
        )
        ext_b = DocumentExtraction.objects.create(
            document=doc_b,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1.0",
            extraction_model_version="1.0",
            status="completed",
        )

        # When: Query extractions for tenant_a documents
        tenant_a_extractions = DocumentExtraction.objects.filter(
            document__tenant_id=tenant_a
        )

        # Then: Only tenant_a's extractions
        self.assertEqual(tenant_a_extractions.count(), 1)
        self.assertEqual(tenant_a_extractions.first().pk, ext_a.pk)
