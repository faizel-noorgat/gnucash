"""
DocumentAttachment serializers
"""
from rest_framework import serializers
from business_documents.models import DocumentAttachment


class DocumentAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for DocumentAttachment"""
    file_size_display = serializers.CharField(read_only=True)

    class Meta:
        model = DocumentAttachment
        fields = [
            'guid',
            'filename',
            'content_type',
            'size',
            'file_size_display',
            'storage_key',
            'description',
            'uploaded_at',
            'uploaded_by',
        ]
        read_only_fields = [
            'guid',
            'storage_key',
            'uploaded_at',
            'uploaded_by',
        ]


class DocumentAttachmentUploadSerializer(serializers.Serializer):
    """Serializer for uploading an attachment"""
    file = serializers.FileField()
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB")

        # Check file type
        allowed_types = [
            'application/pdf',
            'image/jpeg',
            'image/png',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        ]
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(f"File type {value.content_type} not allowed")

        return value
