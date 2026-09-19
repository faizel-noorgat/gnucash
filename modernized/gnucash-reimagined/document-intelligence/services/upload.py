"""Upload service — handles document upload with provenance capture.

Responsibilities:
1. Compute SHA-256 of uploaded bytes (BR-DI-001)
2. Upload to S3 with Object Lock (BR-DI-002)
3. Run duplicate detection (BR-DI-005)
4. Persist Document row with full provenance (BR-DI-008)
5. Queue OCR/extraction task
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import Document, DocumentSource, DocumentStatus

logger = logging.getLogger(__name__)


class ObjectStorageClient(Protocol):
    """Protocol for object-storage backends (S3, MinIO, etc.)."""

    def upload_file(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str,
        enable_object_lock: bool = True,
    ) -> str:
        """Upload bytes; return the object key."""
        ...

    def get_presigned_url(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        """Return a presigned download URL."""
        ...


class UploadService:
    """Orchestrates document upload."""

    def __init__(self, storage_client: ObjectStorageClient) -> None:
        self.storage = storage_client
        self.conf = settings.DOCUMENT_INTELLIGENCE

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
        - Writes to object storage (immutable)
        - Creates Document row
        - Queues OCR task (if not in synchronous test mode)
        """
        # 1. Compute content hash (BR-DI-001)
        content_hash = Document.compute_sha256(file_bytes)

        # 2. Generate S3 key
        doc_guid = uuid.uuid4()
        key = self._build_object_key(tenant_id, doc_guid, filename)

        # 3. Upload to S3 with Object Lock (BR-DI-002)
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

            duplicate_service = DuplicateDetectionService()
            duplicate_service.detect_and_mark(document)

        # 6. Queue OCR task (async)
        from ..tasks.ocr import run_ocr_task

        run_ocr_task.delay(str(document.guid))

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
        """Build S3 key: tenant/guid/filename."""
        return f"tenants/{tenant_id}/documents/{doc_guid}/{filename}"
