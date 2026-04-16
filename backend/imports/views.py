from __future__ import annotations

from django.http import HttpResponse
from rest_framework import generics, viewsets
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
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        return response
