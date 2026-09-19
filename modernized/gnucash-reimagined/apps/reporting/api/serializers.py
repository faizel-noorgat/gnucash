"""API serializers for the Reporting & Analytics bounded context.

Serializers are intentionally minimal stubs in v1. They convert the
domain models (``ReportDefinition``, ``ReportInstance``, ``Dashboard``,
``DashboardWidget``, ``AnalyticQuery``, ``AnalyticInsight``) to / from
the JSON payloads accepted by the API views.

Financial amounts are serialised as strings to avoid floating-point
round-trip loss.
"""

from __future__ import annotations

from rest_framework import serializers


class ReportDefinitionSerializer(serializers.Serializer):
    guid = serializers.UUIDField(read_only=True)
    code = serializers.SlugField()
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False)
    report_type = serializers.ChoiceField(choices=[])  # populated from ReportType
    parameter_schema = serializers.JSONField(required=False)
    default_parameters = serializers.JSONField(required=False)
    is_system = serializers.BooleanField(read_only=True)


class ReportInstanceSerializer(serializers.Serializer):
    guid = serializers.UUIDField(read_only=True)
    definition_code = serializers.SlugField(write_only=True)
    status = serializers.CharField(read_only=True)
    parameters = serializers.JSONField()
    output_format = serializers.ChoiceField(choices=[], required=False)
    result_rows = serializers.JSONField(read_only=True)
    row_count = serializers.IntegerField(read_only=True)
    error_message = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class DashboardSerializer(serializers.Serializer):
    guid = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False)
    is_default = serializers.BooleanField(required=False)
    layout = serializers.JSONField(required=False)


class DashboardWidgetSerializer(serializers.Serializer):
    guid = serializers.UUIDField(read_only=True)
    widget_type = serializers.ChoiceField(choices=[])
    title = serializers.CharField(max_length=255)
    report_definition = serializers.SlugField(allow_null=True, required=False)
    kpi_name = serializers.CharField(max_length=128, allow_blank=True, required=False)
    parameters = serializers.JSONField(required=False)
    visual_config = serializers.JSONField(required=False)
    position = serializers.IntegerField(required=False)


class AnalyticQuerySerializer(serializers.Serializer):
    guid = serializers.UUIDField(read_only=True)
    kind = serializers.ChoiceField(choices=[])
    natural_language_question = serializers.CharField(
        allow_blank=True, required=False
    )
    parameters = serializers.JSONField()
    metrics = serializers.JSONField(read_only=True)


class AnalyticInsightSerializer(serializers.Serializer):
    guid = serializers.UUIDField(read_only=True)
    query = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    evidence = serializers.JSONField(read_only=True)
    narrative = serializers.CharField(read_only=True)
    llm_provider = serializers.CharField(read_only=True)
    llm_model = serializers.CharField(read_only=True)
    confidence_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
