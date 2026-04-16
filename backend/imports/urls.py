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
