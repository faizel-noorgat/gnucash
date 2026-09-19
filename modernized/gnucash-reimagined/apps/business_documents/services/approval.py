"""
Approval service - handles approval workflow execution
"""
from django.db import transaction
from django.utils import timezone
from typing import Optional

from apps.business_documents.models import (
    AccountingDocument,
    ApprovalWorkflow,
    ApprovalStep,
    ApprovalStatus,
    DocumentStatus,
)


class ApprovalService:
    """
    Service for managing document approval workflows.

    Handles approval chain execution, step progression, and status updates.
    """

    @transaction.atomic
    def submit_for_approval(self, document: AccountingDocument, user) -> None:
        """
        Submit a document for approval.

        Creates approval steps based on the applicable workflow.

        Args:
            document: The accounting document to submit
            user: The user submitting the document

        Raises:
            ValueError: If document cannot be submitted for approval
        """
        if document.status not in [DocumentStatus.DRAFT]:
            raise ValueError(f"Document in {document.status} status cannot be submitted for approval")

        # Find applicable workflow
        workflow = self._get_applicable_workflow(document)

        if not workflow:
            # No workflow required - can go straight to approved
            document.status = DocumentStatus.APPROVED
            document.save()
            return

        # Create approval steps from workflow
        for step_template in workflow.steps.all():
            ApprovalStep.objects.create(
                workflow=workflow,
                name=step_template.name,
                step_order=step_template.step_order,
                approver_role=step_template.approver_role,
                approver_user=step_template.approver_user,
                document=document
            )

        # Update document status
        document.status = DocumentStatus.PENDING_APPROVAL
        document.save()

    @transaction.atomic
    def approve_step(self, step: ApprovalStep, user) -> None:
        """
        Approve an approval step.

        If all steps are approved, marks the document as approved.

        Args:
            step: The approval step to approve
            user: The user approving the step

        Raises:
            ValueError: If step cannot be approved
        """
        if step.status != ApprovalStatus.PENDING:
            raise ValueError(f"Step in {step.status} status cannot be approved")

        # Mark step as approved
        step.approve(user)

        # Check if all steps are now approved
        document = step.document
        if document and self._all_steps_approved(document):
            document.status = DocumentStatus.APPROVED
            document.save()

    @transaction.atomic
    def reject_step(self, step: ApprovalStep, user, reason: str = '') -> None:
        """
        Reject an approval step.

        Marks the document as cancelled.

        Args:
            step: The approval step to reject
            user: The user rejecting the step
            reason: Reason for rejection

        Raises:
            ValueError: If step cannot be rejected
        """
        if step.status != ApprovalStatus.PENDING:
            raise ValueError(f"Step in {step.status} status cannot be rejected")

        # Mark step as rejected
        step.reject(user, reason)

        # Mark document as cancelled
        document = step.document
        if document:
            document.status = DocumentStatus.CANCELLED
            document.save()

    def _get_applicable_workflow(self, document: AccountingDocument) -> Optional[ApprovalWorkflow]:
        """
        Find the applicable approval workflow for a document.

        Args:
            document: The accounting document

        Returns:
            ApprovalWorkflow or None if no workflow applies
        """
        # Find active workflows for this tenant
        workflows = ApprovalWorkflow.objects.filter(
            tenant=document.tenant,
            is_active=True,
            applies_to_document_types__contains=[document.document_type]
        )

        # Check threshold
        for workflow in workflows:
            if workflow.threshold_amount is None or document.total >= workflow.threshold_amount:
                return workflow

        return None

    def _all_steps_approved(self, document: AccountingDocument) -> bool:
        """
        Check if all approval steps for a document are approved.

        Args:
            document: The accounting document

        Returns:
            True if all steps are approved, False otherwise
        """
        steps = ApprovalStep.objects.filter(document=document)
        return all(step.status == ApprovalStatus.APPROVED for step in steps)
