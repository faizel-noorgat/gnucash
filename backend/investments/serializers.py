from __future__ import annotations

from rest_framework import serializers

from investments.models import InvestmentAccount, InvestmentLot, Price


class InvestmentAccountSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.full_name', read_only=True)

    class Meta:
        model = InvestmentAccount
        fields = ('id', 'tenant', 'account', 'account_name', 'institution', 'account_number')
        read_only_fields = ('id',)


class InvestmentLotSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentLot
        fields = (
            'id', 'tenant', 'account', 'security_id', 'quantity',
            'purchase_date', 'purchase_price', 'cost_basis', 'is_closed', 'created_at',
        )
        read_only_fields = ('id', 'created_at')


class PriceSerializer(serializers.ModelSerializer):
    commodity_mnemonic = serializers.CharField(source='commodity.mnemonic', read_only=True)

    class Meta:
        model = Price
        fields = ('id', 'commodity', 'commodity_mnemonic', 'currency', 'date', 'source', 'price_type', 'value')
        read_only_fields = ('id',)
