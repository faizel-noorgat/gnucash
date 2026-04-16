from __future__ import annotations

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, viewsets
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
class StripeWebhookView(generics.GenericAPIView):
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        StripeService.handle_webhook(payload, sig_header)
        return HttpResponse(status=200)
