"""
AccountingDocument serializers
"""
from rest_framework import serializers
from business_documents.models import AccountingDocument, DocumentStatus
from .line import DocumentLineSerializer


class AccountingDocumentSerializer(serializers.ModelSerializer):
    """Serializer for AccountingDocument detail view"""
    lines = DocumentLineSerializer(many=True, read_only=True)

    class Meta:
        model = AccountingDocument
        fields = [
            'guid',
            'document_number',
            'reference_number',
            'document_type',
            'direction',
            'party',
            'document_date',
            'due_date',
            'status',
            'currency',
            'subtotal',
            'tax_total',
            'discount_total',
            'total',
            'payment_terms',
            'posted_at',
            'posted_by',
            'journal_entry',
            'description',
            'notes',
            'terms',
            'lines',
            'created_at',
            'updated_at',
            'version',
        ]
        read_only_fields = [
            'guid',
            'status',
            'posted_at',
            'posted_by',
            'journal_entry',
            'subtotal',
            'tax_total',
            'discount_total',
            'total',
            'created_at',
            'updated_at',
            'version',
        ]


class AccountingDocumentListSerializer(serializers.ModelSerializer):
    """Serializer for AccountingDocument list view (lighter weight)"""
    party_name = serializers.CharField(source='party.name', read_only=True)

    class Meta:
        model = AccountingDocument
        fields = [
            'guid',
            'document_number',
            'document_type',
            'direction',
            'party_name',
            'document_date',
            'status',
            'total',
            'currency',
        ]


class DocumentPostSerializer(serializers.Serializer):
    """Serializer for posting a document"""

    def validate(self, attrs):
        """Validate document can be posted"""
        document = self.context.get('document')
        if not document:
            raise serializers.ValidationError("Document not found")

        if document.is_posted:
            raise serializers.ValidationError("Document has already been posted")

        if not document.can_post():
            raise serializers.ValidationError(f"Document in {document.status} status cannot be posted")

        return attrs
