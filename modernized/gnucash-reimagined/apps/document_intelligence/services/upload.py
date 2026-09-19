"""Upload service — handles document upload with provenance capture.

Responsibilities:
1. Compute SHA-256 of uploaded bytes (BR-DI-001)
2. Upload to object storage with Object Lock (BR-DI-002)
3. Run duplicate detection (BR-DI-005)
4. Persist Document row with full provenance (BR-DI-008)

Design:
- Storage backend is injected via Protocol (dependency inversion). When no
  client is supplied, the configured client comes from
  `services.storage.get_storage_client()`.
- Settings are read on every access (see the `conf` property) so that
  `override_settings` and runtime reconfiguration are honoured even when the
  service was constructed before the override was applied.
- OCR/extraction is NOT run inline. OCR/LLM output only *proposes*; it never
  posts journals (BR-DI-009). Extraction runs through OCRService and
  ExtractionService, which append new DocumentExtraction rows.

Implements behavior-contract rules:
- BR-DI-001: content hash computed from the uploaded bytes
- BR-DI-002: original object written immutably (Object Lock requested)
- BR-DI-005: duplicate detection runs as part of upload
- BR-DI-008: provenance fields are complete
- BR-DI-010: tenant-scoped by object-key layout and row data
"""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import Document, DocumentSource, DocumentStatus
from .storage import ObjectStorageClient, get_storage_client

logger = logging.getLogger(__name__)


class UploadService:
    """Orchestrates document upload.

    Usage:
        service = UploadService()
        document = service.upload_document(
            tenant_id=..., legal_entity_id=..., file_bytes=..., filename=...,
            mime_type=..., source=DocumentSource.WEB_UPLOAD, uploaded_by=...,
        )
    """

    def __init__(self, storage_client: ObjectStorageClient | None = None) -> None:
        """Initialize the upload service.

        Args:
            storage_client: Object-storage backend. If None, the configured
                client is obtained from `get_storage_client()`.
        """
        self.storage = storage_client or get_storage_client()

    @property
    def conf(self) -> dict:
        """Document Intelligence settings.

        Read lazily (not cached in __init__) so `override_settings` applied
        around a single call is still respected.
        """
        return settings.DOCUMENT_INTELLIGENCE

    def upload_document(
        self,
        *,
        tenant_id: uuid.UUID,
        legal_entity_id: uuid.UUID | None,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        source: DocumentSource,
        uploaded_by: uuid.UUID | None,
    ) -> Document:
        """Upload a document and return the persisted Document.

        Side effects:
        - Writes to object storage (immutable, Object Lock requested)
        - Creates Document row
        - Runs duplicate detection (BR-DI-005)
        """
        # 1. Compute content hash (BR-DI-001)
        content_hash = Document.compute_sha256(file_bytes)

        # 2. Generate object key
        doc_guid = uuid.uuid4()
        key = self._build_object_key(tenant_id, doc_guid, filename)

        # 3. Upload to object storage with Object Lock (BR-DI-002)
        self.storage.upload_file(
            bucket=self.conf["S3_BUCKET"],
            key=key,
            body=file_bytes,
            content_type=mime_type,
            enable_object_lock=True,
        )

        # 4. Persist Document (BR-DI-008)
        with transaction.atomic():
            document = Document.objects.create(
                guid=doc_guid,
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                original_file_key=key,
                content_hash=content_hash,
                mime_type=mime_type,
                original_filename=filename,
                size_bytes=len(file_bytes),
                source=source,
                uploaded_at=timezone.now(),
                uploaded_by=uploaded_by,
                status=DocumentStatus.UPLOADED,
            )

            # 5. Run duplicate detection (BR-DI-005)
            from .duplicate import DuplicateDetectionService

            DuplicateDetectionService().detect_and_mark(document)

        # 6. OCR/extraction is triggered downstream, never inline: OCR/LLM
        #    output proposes candidates only and cannot post journals
        #    (BR-DI-009).
        logger.info(
            "Uploaded document %s (tenant=%s, hash=%s, key=%s)",
            document.guid,
            tenant_id,
            content_hash[:16],
            key,
        )
        return document

    def _build_object_key(
        self, tenant_id: uuid.UUID, doc_guid: uuid.UUID, filename: str
    ) -> str:
        """Build the object key: tenants/{tenant_id}/documents/{guid}/{filename}."""
        return f"tenants/{tenant_id}/documents/{doc_guid}/{filename}"
