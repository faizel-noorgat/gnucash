"""Serializers for dashboards."""

from __future__ import annotations

from rest_framework import serializers

from ..models import Dashboard, DashboardWidget


class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = [
            "guid",
            "widget_type",
            "title",
            "report_definition",
            "kpi_name",
            "parameters",
            "visual_config",
            "position",
            "cache_ttl_seconds",
        ]
        read_only_fields = ["guid"]


class DashboardSerializer(serializers.ModelSerializer):
    widgets = DashboardWidgetSerializer(many=True, read_only=True)

    class Meta:
        model = Dashboard
        fields = [
            "guid",
            "name",
            "description",
            "is_default",
            "layout",
            "widgets",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["guid", "created_at", "updated_at"]
