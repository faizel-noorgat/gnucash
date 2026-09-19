"""Shared test fixtures for Document Intelligence acceptance tests."""

from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from apps.document_intelligence.models import Document, DocumentSource


@pytest.fixture
def tenant_id():
    """Test tenant ID."""
    return uuid.uuid4()


@pytest.fixture
def legal_entity_id():
    """Test legal entity ID."""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Test user ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF bytes for testing."""
    # Minimal valid PDF
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"


@pytest.fixture
def sample_document(tenant_id, legal_entity_id, user_id, sample_pdf_bytes):
    """Create a test document (not persisted)."""
    return Document(
        tenant_id=tenant_id,
        legal_entity_id=legal_entity_id,
        original_file_key=f"tenants/{tenant_id}/documents/{uuid.uuid4()}/test.pdf",
        content_hash=Document.compute_sha256(sample_pdf_bytes),
        mime_type="application/pdf",
        original_filename="test.pdf",
        size_bytes=len(sample_pdf_bytes),
        source=DocumentSource.WEB_UPLOAD,
        uploaded_at=timezone.now(),
        uploaded_by=user_id,
    )


@pytest.fixture
def storage_client():
    """Mock storage client for tests."""
    from apps.document_intelligence.services.storage import MockStorageClient

    return MockStorageClient()
