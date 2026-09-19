"""Serializers for analytics."""

from __future__ import annotations

from rest_framework import serializers

from ..models import AnalyticInsight, AnalyticQuery


class AnalyticQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticQuery
        fields = [
            "guid",
            "kind",
            "natural_language_question",
            "parameters",
            "metrics",
            "created_at",
        ]
        read_only_fields = ["guid", "metrics", "created_at"]


class AnalyticInsightSerializer(serializers.ModelSerializer):
    query = AnalyticQuerySerializer(read_only=True)

    class Meta:
        model = AnalyticInsight
        fields = [
            "guid",
            "query",
            "status",
            "evidence",
            "narrative",
            "llm_provider",
            "llm_model",
            "confidence_score",
            "reviewed_by",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = [
            "guid",
            "evidence",
            "narrative",
            "llm_provider",
            "llm_model",
            "confidence_score",
            "created_at",
        ]
