from __future__ import annotations

from rest_framework import serializers

from billing.models import StripeEvent, Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            'id', 'tenant', 'stripe_subscription_id', 'status',
            'current_period_start', 'current_period_end',
            'cancel_at_period_end', 'canceled_at', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'stripe_subscription_id', 'created_at', 'updated_at')


class StripeEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = StripeEvent
        fields = ('id', 'stripe_event_id', 'event_type', 'processed', 'created_at')
        read_only_fields = fields
