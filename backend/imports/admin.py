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
