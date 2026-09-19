"""URL configuration for accounting-engine project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("accounting_engine.api.urls")),
]
