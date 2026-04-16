from __future__ import annotations


class BillingError(Exception):
    pass


class StripeWebhookError(BillingError):
    pass


class SubscriptionNotFoundError(BillingError):
    pass
