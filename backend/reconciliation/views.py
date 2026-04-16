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

        from transactions.models import Split
        suggested_splits = SplitSerializer(
            Split.objects.filter(id__in=suggested_ids), many=True
        ).data
        return Response({'suggested_splits': suggested_splits})

    @action(detail=True, methods=['post'])
    def mark_cleared(self, request, pk=None):
        session = self.get_object()
        split_ids = request.data.get('split_ids', [])
        from transactions.models import Split
        Split.objects.filter(id__in=split_ids, tenant=request.tenant).update(reconcile_state='c')
        return Response({'status': 'updated'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        session = self.get_object()
        ReconciliationService.complete_reconciliation(session)
        return Response(self.get_serializer(session).data)
