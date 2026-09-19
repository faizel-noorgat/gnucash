"""
URL configuration for GnuCash Reimagined project.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # API schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Bounded context APIs
    path("api/identity/", include("apps.identity.api.urls")),
    path("api/accounting/", include("apps.accounting.api.urls")),
    path("api/documents/", include("apps.business_documents.api.urls")),
    path("api/intelligence/", include("apps.document_intelligence.api.urls")),
    path("api/reporting/", include("apps.reporting.api.urls")),
]
