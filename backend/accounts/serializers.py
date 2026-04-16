from __future__ import annotations

from rest_framework import serializers

from accounts.models import Account, AccountType, Commodity


# Mapping of account types to their compatible child/parent types
# Ported from GnuCash xaccAccountTypesCompatibleWith
COMPATIBLE_CHILDREN = {
    AccountType.ASSET: {'BANK', 'CASH', 'STOCK', 'MUTUAL', 'RECEIVABLE'},
    AccountType.LIABILITY: {'CREDIT', 'PAYABLE'},
    AccountType.EQUITY: set(),
    AccountType.INCOME: set(),
    AccountType.EXPENSE: set(),
}


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
            'id', 'tenant', 'parent', 'name', 'full_name', 'code', 'description',
            'account_type', 'commodity', 'commodity_scu', 'hidden', 'placeholder',
            'color', 'notes', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'tenant', 'full_name', 'created_at', 'updated_at')

    def validate_account_type(self, value):
        instance = self.instance
        if instance and instance.splits.exists():
            if instance.account_type != value:
                raise serializers.ValidationError(
                    'Cannot change account type after transactions exist.'
                )
        return value

    def validate_parent(self, value):
        if value and value.pk == self.instance.pk:
            raise serializers.ValidationError('An account cannot be its own parent.')
        return value

    def create(self, validated_data):
        parent = validated_data.get('parent')
        if parent:
            validated_data['full_name'] = f'{parent.full_name}:{validated_data["name"]}'
        else:
            validated_data['full_name'] = validated_data['name']
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'name' in validated_data or 'parent' in validated_data:
            parent = validated_data.get('parent', instance.parent)
            name = validated_data.get('name', instance.name)
            if parent:
                validated_data['full_name'] = f'{parent.full_name}:{name}'
            else:
                validated_data['full_name'] = name
        return super().update(instance, validated_data)


class CommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model = Commodity
        fields = ('id', 'namespace', 'mnemonic', 'fullname', 'cusip', 'fraction')
        read_only_fields = ('id',)
