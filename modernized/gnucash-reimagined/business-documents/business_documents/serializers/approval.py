"""
Approval workflow serializers
"""
from rest_framework import serializers
from business_documents.models import ApprovalWorkflow, ApprovalStep


class ApprovalStepSerializer(serializers.ModelSerializer):
    """Serializer for ApprovalStep"""

    class Meta:
        model = ApprovalStep
        fields = [
            'guid',
            'name',
            'step_order',
            'approver_role',
            'approver_user',
            'status',
            'approved_at',
            'approved_by',
            'rejection_reason',
            'document',
        ]
        read_only_fields = [
            'guid',
            'status',
            'approved_at',
            'approved_by',
            'rejection_reason',
        ]


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    """Serializer for ApprovalWorkflow"""
    steps = ApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalWorkflow
        fields = [
            'guid',
            'name',
            'description',
            'applies_to_document_types',
            'threshold_amount',
            'is_active',
            'steps',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'guid',
            'created_at',
            'updated_at',
        ]
