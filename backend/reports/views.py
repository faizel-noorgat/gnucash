from __future__ import annotations

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from reports.services import ReportService


class BalanceSheetView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        as_of = request.query_params.get('as_of')
        if not as_of:
            return Response({'error': 'as_of query parameter required'}, status=400)
        data = ReportService.balance_sheet(request.tenant, as_of)
        return Response(data)


class IncomeStatementView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not start or not end:
            return Response({'error': 'start_date and end_date required'}, status=400)
        data = ReportService.income_statement(request.tenant, start, end)
        return Response(data)


class CashFlowView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not start or not end:
            return Response({'error': 'start_date and end_date required'}, status=400)
        data = ReportService.cash_flow(request.tenant, start, end)
        return Response(data)


class NetWorthView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        as_of = request.query_params.get('as_of')
        if not as_of:
            return Response({'error': 'as_of query parameter required'}, status=400)
        data = ReportService.net_worth(request.tenant, as_of)
        return Response(data)
