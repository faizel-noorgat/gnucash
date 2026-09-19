"""
Approval workflow models - configurable approval chains for documents
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class ApprovalStatus(models.TextChoices):
    """Status of an approval step"""
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    SKIPPED = 'SKIPPED', 'Skipped'


class ApprovalWorkflow(models.Model):
    """
    Configurable approval workflow for accounting documents.

    Defines the approval chain with multiple steps.
    """
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'identity.Tenant',
        on_delete=models.CASCADE,
        related_name='approval_workflows',
        db_index=True
    )

    # Workflow identification
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Document types this workflow applies to
    applies_to_document_types = models.JSONField(
        default=list,
        help_text="List of DocumentType values this workflow applies to"
    )

    # Threshold (optional - only require approval above certain amount)
    threshold_amount = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Minimum amount requiring approval"
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_workflows'
    )

    class Meta:
        db_table = 'business_documents_approval_workflow'
        verbose_name = 'Approval Workflow'
        verbose_name_plural = 'Approval Workflows'
        ordering = ['name']

    def __str__(self):
        return self.name


class ApprovalStep(models.Model):
    """
    Individual approval step in a workflow.

    Steps are executed in order (by step_order).
    """
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name='steps'
    )

    # Step identification
    name = models.CharField(max_length=255)
    step_order = models.PositiveIntegerField(help_text="Order of execution")

    # Approver
    approver_role = models.CharField(
        max_length=100,
        blank=True,
        help_text="Role required to approve (e.g., 'APPROVER', 'MANAGER')"
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_steps',
        help_text="Specific user approver (optional)"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING
    )

    # Action
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_steps'
    )
    rejection_reason = models.TextField(blank=True)

    # Document this approval is for
    document = models.ForeignKey(
        'AccountingDocument',
        on_delete=models.CASCADE,
        related_name='approval_steps',
        null=True,
        blank=True
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'business_documents_approval_step'
        verbose_name = 'Approval Step'
        verbose_name_plural = 'Approval Steps'
        ordering = ['step_order']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def approve(self, user):
        """Mark this step as approved"""
        self.status = ApprovalStatus.APPROVED
        self.approved_at = timezone.now()
        self.approved_by = user
        self.save()

    def reject(self, user, reason=''):
        """Mark this step as rejected"""
        self.status = ApprovalStatus.REJECTED
        self.approved_by = user
        self.rejection_reason = reason
        self.save()
