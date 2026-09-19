"""
DocumentLine serializers
"""
from rest_framework import serializers
from business_documents.models import DocumentLine


class DocumentLineSerializer(serializers.ModelSerializer):
    """Serializer for DocumentLine"""

    class Meta:
        model = DocumentLine
        fields = [
            'guid',
            'line_number',
            'description',
            'quantity',
            'unit_price',
            'account',
            'tax_rule',
            'tax_included',
            'discount_ordering_mode',
            'discount_percentage',
            'discount_amount',
            'subtotal',
            'discount_value',
            'tax_value',
            'total',
            'project',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'guid',
            'subtotal',
            'discount_value',
            'tax_value',
            'total',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs):
        """Validate line item data"""
        quantity = attrs.get('quantity')
        unit_price = attrs.get('unit_price')

        if quantity is not None and quantity <= 0:
            raise serializers.ValidationError("Quantity must be positive")

        if unit_price is not None and unit_price < 0:
            raise serializers.ValidationError("Unit price cannot be negative")

        return attrs
