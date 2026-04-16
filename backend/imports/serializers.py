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
