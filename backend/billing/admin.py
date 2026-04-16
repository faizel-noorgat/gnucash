from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import register

from billing.models import StripeEvent, Subscription


@register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'status', 'current_period_end', 'cancel_at_period_end')
    list_filter = ('status',)
    search_fields = ('tenant__name', 'stripe_subscription_id')
    readonly_fields = ('id', 'stripe_subscription_id', 'created_at', 'updated_at')


@register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_type', 'stripe_event_id', 'processed', 'created_at')
    list_filter = ('processed', 'event_type')
    readonly_fields = ('id', 'stripe_event_id', 'event_type', 'raw_payload', 'created_at')
