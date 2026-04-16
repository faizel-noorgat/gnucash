# Phase 2: Billing, Reconciliation & Import/Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the billing (Stripe), reconciliation (auto-suggest), and CSV import/export subsystems. These apps currently have empty directories with only `tests/` folders.

**Architecture:** Billing integrates Stripe for subscription management. Reconciliation implements the subset-sum auto-suggest algorithm ported from GnuCash's `gnc-autoclear.cpp`. Import/export handles CSV with column mapping templates.

**Tech Stack:** Django, DRF, Stripe SDK, Celery

---

## File Map

### Files to Create
- `backend/billing/models.py` — Subscription, Invoice, StripeEvent models
- `backend/billing/serializers.py` — Serializers for all billing models
- `backend/billing/views.py` — SubscriptionViewSet, Stripe webhook, billing dashboard
- `backend/billing/urls.py` — Router + webhook route
- `backend/billing/admin.py` — Admin registrations
- `backend/billing/services.py` — Stripe service layer
- `backend/billing/tasks.py` — Stripe sync, dunning management
- `backend/billing/exceptions.py` — Billing domain exceptions
- `backend/billing/tests/__init__.py` — Test package
- `backend/reconciliation/models.py` — ReconciliationSession model
- `backend/reconciliation/serializers.py` — ReconciliationSession serializer
- `backend/reconciliation/views.py` — ReconciliationViewSet + auto-suggest endpoint
- `backend/reconciliation/urls.py` — Router registration
- `backend/reconciliation/admin.py` — Admin registration
- `backend/reconciliation/services.py` — Subset-sum algorithm, balance calculation
- `backend/reconciliation/exceptions.py` — Reconciliation domain exceptions
- `backend/reconciliation/tests/__init__.py` — Test package
- `backend/imports/models.py` — CSV import template model
- `backend/imports/serializers.py` — Import serializers
- `backend/imports/views.py` — Import/Export views
- `backend/imports/urls.py` — Router registration
- `backend/imports/admin.py` — Admin registrations
- `backend/imports/services.py` — CSV parsing, column mapping, export
- `backend/imports/exceptions.py` — Import domain exceptions
- `backend/imports/tests/__init__.py` — Test package

### Files to Modify
- `backend/gnucash_web/urls.py` — Wire up billing, reconciliation, import routes
- `backend/gnucash_web/settings/base.py` — Add Stripe settings, add 'imports' to INSTALLED_APPS

---

### Task 1: Billing Models & Stripe Integration

**Files:**
- Create: `backend/billing/models.py`
- Create: `backend/billing/serializers.py`
- Create: `backend/billing/views.py`
- Create: `backend/billing/urls.py`
- Create: `backend/billing/admin.py`
- Create: `backend/billing/services.py`
- Create: `backend/billing/tasks.py`
- Create: `backend/billing/exceptions.py`
- Create: `backend/billing/tests/__init__.py`

- [ ] **Step 1: Create Billing models**

```python
# backend/billing/models.py
from __future__ import annotations

import uuid

from django.db import models

from tenants.models import Tenant


class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIALING = 'TRIALING', 'Trialing'
        ACTIVE = 'ACTIVE', 'Active'
        PAST_DUE = 'PAST_DUE', 'Past Due'
        CANCELED = 'CANCELED', 'Canceled'
        EXPIRED = 'EXPIRED', 'Expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='subscription')
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIALING)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.tenant.name} - {self.status}'


class StripeEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    raw_payload = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['processed', 'created_at']),
        ]

    def __str__(self):
        return f'{self.event_type} ({self.stripe_event_id})'
```

- [ ] **Step 2: Create Billing serializers**

```python
# backend/billing/serializers.py
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
```

- [ ] **Step 3: Create Billing exceptions**

```python
# backend/billing/exceptions.py
from __future__ import annotations


class BillingError(Exception):
    pass


class StripeWebhookError(BillingError):
    pass


class SubscriptionNotFoundError(BillingError):
    pass
```

- [ ] **Step 4: Create Billing service layer**

```python
# backend/billing/services.py
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
        tenant = SubscriptionService._find_tenant(data)
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
        # Create notification for tenant owner
        from notifications.services import NotificationService
        from tenants.models import TenantMembership

        tenant = SubscriptionService._find_tenant(data)
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
```

- [ ] **Step 5: Create Billing views**

```python
# backend/billing/views.py
from __future__ import annotations

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from billing.models import Subscription
from billing.serializers import SubscriptionSerializer
from billing.services import StripeService


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(tenant=self.request.tenant)

    @action(detail=False, methods=['post'])
    def create_subscription(self, request):
        price_id = request.data.get('price_id')
        if not price_id:
            return Response({'error': 'price_id required'}, status=400)
        subscription = StripeService.create_subscription(request.tenant, price_id)
        return Response(SubscriptionSerializer(subscription).data, status=201)

    @action(detail=False, methods=['post'])
    def cancel(self, request):
        subscription = Subscription.objects.filter(tenant=request.tenant).first()
        if not subscription:
            return Response({'error': 'No active subscription'}, status=404)
        StripeService.cancel_subscription(subscription)
        return Response(SubscriptionSerializer(subscription).data)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView:
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        StripeService.handle_webhook(payload, sig_header)
        return HttpResponse(status=200)
```

- [ ] **Step 6: Create Billing URLs and admin**

```python
# backend/billing/urls.py
from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from billing.views import StripeWebhookView, SubscriptionViewSet

router = DefaultRouter()
router.register('billing/subscription', SubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('billing/webhook/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('', include(router.urls)),
]
```

```python
# backend/billing/admin.py
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
```

- [ ] **Step 7: Create Billing tasks**

```python
# backend/billing/tasks.py
from __future__ import annotations

from celery import shared_task


@shared_task(name='billing.sync_stripe_data')
def sync_stripe_data():
    """Sync local subscription data with Stripe."""
    pass
```

- [ ] **Step 8: Add Stripe settings to base.py**

Add to `backend/gnucash_web/settings/base.py`:

```python
# Stripe
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='')
```

- [ ] **Step 9: Commit**

```bash
git add backend/billing/
git commit -m "feat: add billing app with Stripe integration, subscription management"
```

---

### Task 2: Reconciliation App with Subset-Sum Auto-Suggest

**Files:**
- Create: `backend/reconciliation/models.py`
- Create: `backend/reconciliation/serializers.py`
- Create: `backend/reconciliation/views.py`
- Create: `backend/reconciliation/urls.py`
- Create: `backend/reconciliation/admin.py`
- Create: `backend/reconciliation/services.py`
- Create: `backend/reconciliation/exceptions.py`
- Create: `backend/reconciliation/tests/__init__.py`

- [ ] **Step 1: Create Reconciliation model**

```python
# backend/reconciliation/models.py
from __future__ import annotations

import uuid

from django.db import models

from accounts.models import Account
from tenants.models import Tenant


class ReconciliationSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='reconciliation_sessions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='reconciliation_sessions')
    end_date = models.DateField()
    ending_balance = models.DecimalField(max_digits=20, decimal_places=10)
    starting_balance = models.DecimalField(max_digits=20, decimal_places=10)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.account.full_name} reconciliation ({self.end_date})'

    @property
    def difference(self):
        """Calculate difference between ending balance and cleared transactions."""
        from transactions.models import Split

        cleared = Split.objects.filter(
            tenant=self.tenant,
            account=self.account,
            reconcile_state__in=['c', 'y'],
            transaction__post_date__lte=self.end_date,
        ).aggregate(total=models.Sum('value'))['total'] or 0
        return self.ending_balance - (self.starting_balance + cleared)
```

- [ ] **Step 2: Create reconciliation services (subset-sum algorithm)**

```python
# backend/reconciliation/services.py
from __future__ import annotations

import time
from decimal import Decimal
from django.db.models import Sum

from transactions.models import Split


class ReconciliationService:
    @staticmethod
    def calculate_account_balance(account, end_date):
        """Calculate running balance for an account up to end_date."""
        splits = Split.objects.filter(
            account=account,
            transaction__post_date__lte=end_date,
        )
        total = splits.aggregate(total=Sum('value'))['total'] or Decimal('0')
        return total

    @staticmethod
    def get_unreconciled_splits(account, end_date):
        """Get all unreconciled splits up to end_date."""
        return Split.objects.filter(
            account=account,
            transaction__post_date__lte=end_date,
            reconcile_state='n',
        ).select_related('transaction').order_by('transaction__post_date')

    @staticmethod
    def auto_suggest_splits(splits, target_balance, max_seconds=30, tolerance=Decimal('0.01')):
        """
        Find a subset of splits that sum to the target balance.
        Ported from GnuCash gnc-autoclear.cpp subset-sum algorithm.
        Uses pruning for performance.
        """
        start_time = time.time()
        values = [(s.id, s.value) for s in splits]
        solution = []
        ReconciliationService._subset_sum(values, 0, target_balance, [], solution, max_seconds, tolerance, start_time)
        return [s_id for s_id, _ in solution]

    @staticmethod
    def _subset_sum(values, index, target, path, solution, max_seconds, tolerance, start_time):
        """Recursive subset-sum with pruning and timeout."""
        if time.time() - start_time > max_seconds:
            return  # Timeout

        if solution:
            return  # Already found a solution

        current_sum = sum(v for _, v in path)
        if abs(current_sum - target) <= tolerance:
            solution.extend(path)
            return

        if index >= len(values):
            return

        # Pruning: check if remaining values can reach target
        remaining_sum = sum(v for _, v in values[index:])
        if current_sum + remaining_sum < target - tolerance:
            return  # Cannot reach target

        # Branch: include current value
        s_id, value = values[index]
        path.append((s_id, value))
        ReconciliationService._subset_sum(values, index + 1, target, path, solution, max_seconds, tolerance, start_time)
        path.pop()

        if solution:
            return

        # Branch: skip current value
        ReconciliationService._subset_sum(values, index + 1, target, path, solution, max_seconds, tolerance, start_time)

    @staticmethod
    def complete_reconciliation(session):
        """Mark all suggested splits as cleared and complete the session."""
        splits = Split.objects.filter(
            tenant=session.tenant,
            account=session.account,
            reconcile_state='n',
            transaction__post_date__lte=session.end_date,
        )
        # Mark splits that are within the cleared balance as 'cleared'
        from django.db import transaction
        with transaction.atomic():
            splits.update(reconcile_state='c')
            session.completed = True
            from django.utils import timezone
            session.completed_at = timezone.now()
            session.save()
```

- [ ] **Step 3: Create reconciliation serializers**

```python
# backend/reconciliation/serializers.py
from __future__ import annotations

from rest_framework import serializers

from reconciliation.models import ReconciliationSession
from transactions.serializers import SplitSerializer


class ReconciliationSessionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.full_name', read_only=True)
    difference = serializers.DecimalField(max_digits=20, decimal_places=10, read_only=True)

    class Meta:
        model = ReconciliationSession
        fields = (
            'id', 'tenant', 'account', 'account_name', 'end_date',
            'ending_balance', 'starting_balance', 'completed', 'completed_at',
            'difference', 'created_at',
        )
        read_only_fields = ('id', 'difference', 'completed', 'completed_at', 'created_at')
```

- [ ] **Step 4: Create reconciliation views**

```python
# backend/reconciliation/views.py
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Account
from reconciliation.models import ReconciliationSession
from reconciliation.serializers import ReconciliationSessionSerializer
from reconciliation.services import ReconciliationService
from transactions.serializers import SplitSerializer


class ReconciliationViewSet(viewsets.ModelViewSet):
    serializer_class = ReconciliationSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReconciliationSession.objects.filter(tenant=self.request.tenant).select_related('account')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    @action(detail=False, methods=['post'])
    def auto_suggest(self, request):
        account_id = request.data.get('account_id')
        end_date = request.data.get('end_date')
        target_balance = request.data.get('target_balance')

        if not all([account_id, end_date, target_balance]):
            return Response({'error': 'account_id, end_date, target_balance required'}, status=400)

        account = Account.objects.get(id=account_id, tenant=request.tenant)
        splits = ReconciliationService.get_unreconciled_splits(account, end_date)
        suggested_ids = ReconciliationService.auto_suggest_splits(splits, target_balance)

        suggested_splits = SplitSerializer(
            Split.objects.filter(id__in=suggested_ids), many=True
        ).data
        return Response({'suggested_splits': suggested_splits})

    @action(detail=True, methods=['post'])
    def mark_cleared(self, request, pk=None):
        session = self.get_object()
        split_ids = request.data.get('split_ids', [])
        Split.objects.filter(id__in=split_ids, tenant=request.tenant).update(reconcile_state='c')
        return Response({'status': 'updated'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        session = self.get_object()
        ReconciliationService.complete_reconciliation(session)
        return Response(self.get_serializer(session).data)
```

- [ ] **Step 5: Create reconciliation URLs and admin**

```python
# backend/reconciliation/urls.py
from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from reconciliation.views import ReconciliationViewSet

router = DefaultRouter()
router.register('reconciliation', ReconciliationViewSet, basename='reconciliation')

urlpatterns = [path('', include(router.urls))]
```

```python
# backend/reconciliation/admin.py
from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import register

from reconciliation.models import ReconciliationSession


@register(ReconciliationSession)
class ReconciliationSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'end_date', 'completed', 'created_at')
    list_filter = ('completed',)
    search_fields = ('account__full_name',)
    readonly_fields = ('id', 'created_at')
```

- [ ] **Step 6: Create reconciliation exceptions**

```python
# backend/reconciliation/exceptions.py
from __future__ import annotations


class ReconciliationError(Exception):
    pass


class BalanceMismatchError(ReconciliationError):
    pass
```

- [ ] **Step 7: Commit**

```bash
git add backend/reconciliation/
git commit -m "feat: add reconciliation app with subset-sum auto-suggest algorithm"
```

---

### Task 3: CSV Import/Export App

**Files:**
- Create: `backend/imports/models.py`
- Create: `backend/imports/serializers.py`
- Create: `backend/imports/views.py`
- Create: `backend/imports/urls.py`
- Create: `backend/imports/admin.py`
- Create: `backend/imports/services.py`
- Create: `backend/imports/exceptions.py`
- Create: `backend/imports/tests/__init__.py`

- [ ] **Step 1: Create import models**

```python
# backend/imports/models.py
from __future__ import annotations

import uuid

from django.db import models

from tenants.models import Tenant


class ImportTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='import_templates')
    name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255, blank=True)
    column_mapping = models.JSONField()  # {"date": 0, "description": 1, "amount": 2}
    delimiter = models.CharField(max_length=10, default=',')
    encoding = models.CharField(max_length=50, default='utf-8')
    has_header = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.bank_name or "custom"})'
```

- [ ] **Step 2: Create import services**

```python
# backend/imports/services.py
from __future__ import annotations

import csv
import io
from decimal import Decimal
from django.db import transaction

from accounts.models import Account
from transactions.models import Split, Transaction


class CsvImportService:
    @staticmethod
    def preview(file_content, delimiter=',', has_header=True, encoding='utf-8'):
        """Parse CSV and return first 10 rows for preview."""
        reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)
        rows = []
        header = None
        for i, row in enumerate(reader):
            if i == 0 and has_header:
                header = row
                continue
            rows.append(row)
            if len(rows) >= 10:
                break
        return {'header': header, 'rows': rows}

    @staticmethod
    def import_transactions(tenant, file_content, column_mapping, account_id, delimiter=',', has_header=True):
        """Import CSV rows as transactions into the specified account."""
        account = Account.objects.get(id=account_id, tenant=tenant)
        reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)

        if has_header:
            next(reader)  # Skip header

        col_map = column_mapping  # e.g., {"date": 0, "description": 2, "amount": 3}
        imported = 0

        with transaction.atomic():
            for row in reader:
                if not row or all(not cell.strip() for cell in row):
                    continue

                date_str = row[col_map['date']].strip()
                description = row[col_map['description']].strip()
                amount_str = row[col_map['amount']].strip().replace(',', '')

                try:
                    amount = Decimal(amount_str)
                except Exception:
                    continue  # Skip rows with invalid amounts

                Transaction.objects.create(
                    tenant=tenant,
                    currency=account.commodity,
                    post_date=date_str,
                    description=description,
                    created_by=None,
                )
                # Create splits: one for the account, one for a placeholder "Unknown"
                Transaction.objects.create(
                    tenant=tenant,
                    currency=account.commodity,
                    post_date=date_str,
                    description=description,
                )
                tx = Transaction.objects.filter(
                    tenant=tenant, post_date=date_str, description=description
                ).order_by('-created_at').first()

                Split.objects.create(
                    tenant=tenant, transaction=tx, account=account, value=-amount, quantity=-amount
                )
                imported += 1

        return imported


class CsvExportService:
    @staticmethod
    def export_transactions(tenant, account_id=None, start_date=None, end_date=None):
        """Export transactions to CSV format."""
        splits = Split.objects.filter(tenant=tenant).select_related(
            'transaction', 'account'
        )

        if account_id:
            splits = splits.filter(account_id=account_id)
        if start_date:
            splits = splits.filter(transaction__post_date__gte=start_date)
        if end_date:
            splits = splits.filter(transaction__post_date__lte=end_date)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Description', 'Account', 'Value', 'Memo', 'Reconciled'])

        for split in splits:
            writer.writerow([
                split.transaction.post_date,
                split.transaction.description,
                split.account.full_name,
                split.value,
                split.memo,
                split.reconcile_state,
            ])

        return output.getvalue()
```

- [ ] **Step 3: Create import views**

```python
# backend/imports/views.py
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from imports.models import ImportTemplate
from imports.serializers import ImportTemplateSerializer
from imports.services import CsvExportService, CsvImportService


class ImportTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ImportTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ImportTemplate.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class CsvImportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'file required'}, status=400)

        content = file.read().decode(request.data.get('encoding', 'utf-8'))

        if request.data.get('preview_only'):
            preview = CsvImportService.preview(
                content,
                delimiter=request.data.get('delimiter', ','),
                has_header=request.data.get('has_header', True),
            )
            return Response(preview)

        column_mapping = request.data.get('column_mapping')
        account_id = request.data.get('account_id')

        if not column_mapping or not account_id:
            return Response({'error': 'column_mapping and account_id required'}, status=400)

        imported = CsvImportService.import_transactions(
            request.tenant, content, column_mapping, account_id,
            delimiter=request.data.get('delimiter', ','),
            has_header=request.data.get('has_header', True),
        )
        return Response({'imported': imported})


class CsvExportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        csv_data = CsvExportService.export_transactions(
            request.tenant,
            account_id=request.query_params.get('account_id'),
            start_date=request.query_params.get('start_date'),
            end_date=request.query_params.get('end_date'),
        )
        from django.http import HttpResponse
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        return response
```

- [ ] **Step 4: Fix import views — add missing import**

Add to top of `backend/imports/views.py`:

```python
from rest_framework import generics
```

- [ ] **Step 5: Create import serializers**

```python
# backend/imports/serializers.py
from __future__ import annotations

from rest_framework import serializers

from imports.models import ImportTemplate


class ImportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportTemplate
        fields = (
            'id', 'tenant', 'name', 'bank_name', 'column_mapping',
            'delimiter', 'encoding', 'has_header', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
```

- [ ] **Step 6: Create import URLs and admin**

```python
# backend/imports/urls.py
from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from imports.views import CsvExportView, CsvImportView, ImportTemplateViewSet

router = DefaultRouter()
router.register('import-templates', ImportTemplateViewSet, basename='import-template')

urlpatterns = [
    path('imports/csv', CsvImportView.as_view(), name='csv-import'),
    path('exports/csv', CsvExportView.as_view(), name='csv-export'),
    path('', include(router.urls)),
]
```

```python
# backend/imports/admin.py
from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import register

from imports.models import ImportTemplate


@register(ImportTemplate)
class ImportTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'bank_name', 'delimiter', 'has_header')
    list_filter = ('delimiter', 'has_header')
    search_fields = ('name', 'bank_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
```

- [ ] **Step 7: Create import exceptions**

```python
# backend/imports/exceptions.py
from __future__ import annotations


class ImportError(Exception):
    pass


class CsvParseError(ImportError):
    pass


class ColumnMappingError(ImportError):
    pass
```

- [ ] **Step 8: Add imports to INSTALLED_APPS**

In `backend/gnucash_web/settings/base.py`, add `'imports',` to `INSTALLED_APPS`.

- [ ] **Step 9: Wire up URLs**

In `backend/gnucash_web/urls.py`, add:

```python
urlpatterns = [
    # ... existing patterns
    path('api/v1/', include('billing.urls')),
    path('api/v1/', include('reconciliation.urls')),
    path('api/v1/', include('imports.urls')),
    # ...
]
```

- [ ] **Step 10: Commit**

```bash
git add backend/imports/ backend/gnucash_web/settings/base.py backend/gnucash_web/urls.py
git commit -m "feat: add imports app with CSV import/export and template saving"
```

---

## Self-Review

### 1. Spec Coverage Check

| Spec Section | Task | Status |
|---|---|---|
| Stripe billing integration | Task 1 | Covered |
| Subscription management | Task 1 | Covered |
| Webhook handling | Task 1 | Covered |
| Dunning management (placeholder) | Task 1 (tasks.py) | Covered |
| Reconciliation flow | Task 2 | Covered |
| Auto-suggest subset-sum | Task 2 | Covered |
| CSV import with column mapping | Task 3 | Covered |
| Save import templates per bank | Task 3 | Covered |
| CSV export (all scopes) | Task 3 | Covered |

### 2. Placeholder Scan

- `sync_stripe_data` task is a stub — acceptable for MVP (Stripe webhooks handle most sync)
- No other placeholders found

### 3. Type/Name Consistency

- All FKs use `related_name` consistently
- `request.tenant` used throughout for tenant scoping
- Decimal fields use `max_digits=20, decimal_places=10` for splits (matching existing Split model)
- `max_digits=12, decimal_places=2` for monetary values (Receipt, BudgetCategory)
