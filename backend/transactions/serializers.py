from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from transactions.models import Split, Transaction


class SplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Split
        fields = (
            'id', 'tenant', 'transaction', 'account', 'memo', 'action',
            'reconcile_state', 'reconcile_date', 'value', 'quantity', 'created_at',
        )
        read_only_fields = ('id', 'tenant', 'transaction', 'created_at')


class TransactionSerializer(serializers.ModelSerializer):
    splits = SplitSerializer(many=True)

    class Meta:
        model = Transaction
        fields = (
            'id', 'tenant', 'guid', 'currency', 'num', 'post_date', 'enter_date',
            'description', 'notes', 'created_by', 'created_at', 'updated_at', 'splits',
        )
        read_only_fields = ('id', 'guid', 'enter_date', 'created_by', 'created_at', 'updated_at')

    def validate_splits(self, value):
        if not value:
            raise serializers.ValidationError('A transaction must have at least 2 splits.')
        if len(value) < 2:
            raise serializers.ValidationError('A transaction must have at least 2 splits.')
        total = sum(Decimal(s.get('value', 0)) for s in value)
        if total != 0:
            raise serializers.ValidationError(f'Transaction splits must sum to zero. Current sum: {total}')
        return value

    def create(self, validated_data):
        splits_data = validated_data.pop('splits')
        transaction = Transaction.objects.create(**validated_data)
        for split_data in splits_data:
            Split.objects.create(transaction=transaction, tenant=transaction.tenant, **split_data)
        return transaction

    def update(self, instance, validated_data):
        splits_data = validated_data.pop('splits', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if splits_data is not None:
            instance.splits.all().delete()
            for split_data in splits_data:
                Split.objects.create(transaction=instance, tenant=instance.tenant, **split_data)
        return instance
