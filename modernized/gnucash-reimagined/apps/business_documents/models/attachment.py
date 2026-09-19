"""
DocumentAttachment model - attachments linked to accounting documents
"""
from django.db import models
from django.conf import settings
import uuid

from common.rls.models import TenantDerivedChildModel


class DocumentAttachment(TenantDerivedChildModel):
    """
    Attachment linked to an accounting document.

    Stored in object storage (S3-compatible). Tenancy is inherited from the
    owning document - see ``TenantDerivedChildModel``.
    """

    #: Tenancy is inherited from the owning document, and takes the same shape
    #: the document's does - a real FK to ``Tenant``.
    tenant = models.ForeignKey(
        'identity.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        db_index=True,
    )
    tenant_parent_field = 'document'
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        'AccountingDocument',
        on_delete=models.CASCADE,
        related_name='attachments'
    )

    # File information
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField(help_text="File size in bytes")

    # Object storage reference
    storage_key = models.CharField(
        max_length=500,
        help_text="S3 key or object storage path"
    )

    # Content hash for integrity
    content_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of file content"
    )

    # Description
    description = models.TextField(blank=True)

    # Audit fields
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_attachments'
    )

    class Meta:
        db_table = 'business_documents_document_attachment'
        verbose_name = 'Document Attachment'
        verbose_name_plural = 'Document Attachments'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} ({self.document})"

    @property
    def file_size_display(self):
        """Human-readable file size"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
