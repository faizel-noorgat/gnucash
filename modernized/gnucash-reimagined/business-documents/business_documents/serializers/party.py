"""
Party serializers
"""
from rest_framework import serializers
from business_documents.models import Party, PartyRole


class PartySerializer(serializers.ModelSerializer):
    """Serializer for Party detail view"""

    class Meta:
        model = Party
        fields = [
            'guid',
            'name',
            'display_name',
            'roles',
            'email',
            'phone',
            'website',
            'address',
            'tax_id',
            'currency',
            'payment_terms',
            'tax_table',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['guid', 'created_at', 'updated_at']

    def validate_roles(self, value):
        """Validate that roles are valid PartyRole choices"""
        valid_roles = [choice.value for choice in PartyRole]
        for role in value:
            if role not in valid_roles:
                raise serializers.ValidationError(f"Invalid role: {role}")
        return value


class PartyListSerializer(serializers.ModelSerializer):
    """Serializer for Party list view (lighter weight)"""

    class Meta:
        model = Party
        fields = [
            'guid',
            'name',
            'display_name',
            'roles',
            'email',
            'is_active',
        ]
