"""
API serializers for business_documents
"""
from rest_framework import serializers

from apps.business_documents.models import (
    Party,
    AccountingDocument,
    DocumentLine,
    DocumentAttachment,
    ApprovalWorkflow,
    ApprovalStep,
)


class PartySerializer(serializers.ModelSerializer):
    """Serializer for Party model"""
    # TODO: Implement full serialization with validation
    class Meta:
        model = Party
        fields = '__all__'
        read_only_fields = ('guid', 'created_at', 'updated_at')


class AccountingDocumentSerializer(serializers.ModelSerializer):
    """Serializer for AccountingDocument model"""
    # TODO: Implement full serialization with validation
    class Meta:
        model = AccountingDocument
        fields = '__all__'
        read_only_fields = ('guid', 'created_at', 'updated_at', 'posted_at', 'posted_by', 'journal_entry')


class DocumentLineSerializer(serializers.ModelSerializer):
    """Serializer for DocumentLine model"""
    # TODO: Implement full serialization with validation
    class Meta:
        model = DocumentLine
        fields = '__all__'
        read_only_fields = ('guid', 'created_at', 'updated_at', 'subtotal', 'discount_value', 'tax_value', 'total')


class DocumentAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for DocumentAttachment model"""
    # TODO: Implement full serialization with validation
    class Meta:
        model = DocumentAttachment
        fields = '__all__'
        read_only_fields = ('guid', 'uploaded_at', 'uploaded_by')


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    """Serializer for ApprovalWorkflow model"""
    # TODO: Implement full serialization with validation
    class Meta:
        model = ApprovalWorkflow
        fields = '__all__'
        read_only_fields = ('guid', 'created_at', 'updated_at')


class ApprovalStepSerializer(serializers.ModelSerializer):
    """Serializer for ApprovalStep model"""
    # TODO: Implement full serialization with validation
    class Meta:
        model = ApprovalStep
        fields = '__all__'
        read_only_fields = ('guid', 'created_at', 'updated_at', 'approved_at', 'approved_by')
