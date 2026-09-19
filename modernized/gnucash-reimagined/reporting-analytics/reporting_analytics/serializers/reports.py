"""Serializers for reports."""

from __future__ import annotations

from rest_framework import serializers

from ..models import ReportDefinition, ReportInstance


class ReportDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportDefinition
        fields = [
            "guid",
            "code",
            "name",
            "description",
            "report_type",
            "parameter_schema",
            "default_parameters",
            "is_system",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["guid", "created_at", "updated_at"]


class ReportInstanceSerializer(serializers.ModelSerializer):
    definition = ReportDefinitionSerializer(read_only=True)
    definition_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ReportInstance
        fields = [
            "guid",
            "definition",
            "definition_id",
            "status",
            "parameters",
            "output_format",
            "result_rows",
            "result_artifact_key",
            "row_count",
            "started_at",
            "completed_at",
            "error_message",
            "created_at",
        ]
        read_only_fields = [
            "guid",
            "status",
            "result_rows",
            "result_artifact_key",
            "row_count",
            "started_at",
            "completed_at",
            "error_message",
            "created_at",
        ]
