"""
URL configuration for business documents service
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from business_documents.views import (
    PartyViewSet,
    AccountingDocumentViewSet,
    DocumentLineViewSet,
    DocumentAttachmentViewSet,
    ApprovalWorkflowViewSet
)

# API router
router = DefaultRouter()
router.register(r'parties', PartyViewSet, basename='party')
router.register(r'documents', AccountingDocumentViewSet, basename='document')
router.register(r'workflows', ApprovalWorkflowViewSet, basename='workflow')

# Nested routers for document lines and attachments
from rest_framework_nested import routers as nested_routers

# Document lines
documents_router = nested_routers.NestedDefaultRouter(router, r'documents', lookup='document')
documents_router.register(r'lines', DocumentLineViewSet, basename='document-lines')
documents_router.register(r'attachments', DocumentAttachmentViewSet, basename='document-attachments')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/', include(documents_router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
