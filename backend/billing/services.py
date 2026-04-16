from __future__ import annotations

import stripe
from django.conf import settings

from billing.exceptions import BillingError, StripeWebhookError
from billing.models import StripeEvent, Subscription

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    @staticmethod
    def create_customer(tenant, email, name):
        customer = stripe.Customer.create(
            email=email, name=name, metadata={'tenant_id': str(tenant.id)}
        )
        tenant.stripe_customer_id = customer.id
        tenant.save()
        return customer

    @staticmethod
    def create_subscription(tenant, price_id):
        if not tenant.stripe_customer_id:
            raise BillingError('Tenant must have a Stripe customer ID.')
        sub = stripe.Subscription.create(
            customer=tenant.stripe_customer_id,
            items=[{'price': price_id}],
            metadata={'tenant_id': str(tenant.id)},
        )
        subscription = Subscription.objects.create(
            tenant=tenant,
            stripe_subscription_id=sub.id,
            status=Subscription.Status.TRIALING,
        )
        return subscription

    @staticmethod
    def cancel_subscription(subscription):
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True,
        )
        subscription.cancel_at_period_end = True
        subscription.save()
        return subscription

    @staticmethod
    def handle_webhook(payload, sig_header):
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            raise StripeWebhookError('Invalid payload')
        except stripe.error.SignatureVerificationError:
            raise StripeWebhookError('Invalid signature')

        stripe_event = StripeEvent.objects.create(
            stripe_event_id=event['id'],
            event_type=event['type'],
            raw_payload=event,
        )
        StripeService._process_event(stripe_event)
        return event

    @staticmethod
    def _process_event(stripe_event):
        event_data = stripe_event.raw_payload
        event_type = event_data['type']
        data = event_data['data']['object']

        if event_type == 'customer.subscription.created':
            StripeService._handle_subscription_created(data)
        elif event_type == 'customer.subscription.updated':
            StripeService._handle_subscription_updated(data)
        elif event_type == 'customer.subscription.deleted':
            StripeService._handle_subscription_deleted(data)
        elif event_type == 'invoice.payment_failed':
            StripeService._handle_payment_failed(data)

        stripe_event.processed = True
        stripe_event.save()

    @staticmethod
    def _handle_subscription_created(data):
        tenant = StripeService._find_tenant(data)
        if tenant:
            Subscription.objects.update_or_create(
                stripe_subscription_id=data['id'],
                defaults={
                    'tenant': tenant,
                    'status': Subscription.Status.ACTIVE,
                    'current_period_start': data['current_period_start'],
                    'current_period_end': data['current_period_end'],
                },
            )

    @staticmethod
    def _handle_subscription_updated(data):
        subscription = Subscription.objects.filter(stripe_subscription_id=data['id']).first()
        if subscription:
            subscription.status = data['status']
            subscription.current_period_start = data.get('current_period_start')
            subscription.current_period_end = data.get('current_period_end')
            subscription.cancel_at_period_end = data.get('cancel_at_period_end', False)
            if data.get('canceled_at'):
                subscription.canceled_at = data['canceled_at']
            subscription.save()

    @staticmethod
    def _handle_subscription_deleted(data):
        subscription = Subscription.objects.filter(stripe_subscription_id=data['id']).first()
        if subscription:
            subscription.status = Subscription.Status.EXPIRED
            subscription.save()

    @staticmethod
    def _handle_payment_failed(data):
        from notifications.services import NotificationService
        from tenants.models import TenantMembership

        tenant = StripeService._find_tenant(data)
        if tenant:
            owner = TenantMembership.objects.filter(tenant=tenant, role='OWNER').first()
            if owner:
                NotificationService.create(
                    tenant=tenant,
                    user=owner.user,
                    notification_type='billing.payment_failed',
                    title='Payment Failed',
                    body='Your latest payment could not be processed.',
                )

    @staticmethod
    def _find_tenant(stripe_data):
        from tenants.models import Tenant

        customer_id = stripe_data.get('customer')
        if customer_id:
            return Tenant.objects.filter(stripe_customer_id=customer_id).first()
        metadata = stripe_data.get('metadata', {})
        tenant_id = metadata.get('tenant_id')
        if tenant_id:
            return Tenant.objects.filter(id=tenant_id).first()
        return None
