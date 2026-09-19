"""
Workflow State domain model.

Represents state machines for approvals, intercompany events, etc.
"""
import uuid
from django.db import models
from django.conf import settings


class WorkflowDefinition(models.Model):
    """
    Definition of a workflow state machine.

    Key points:
    - Defines states and transitions
    - Can be used for approvals, document workflows, intercompany events
    - Versioned for historical preservation
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    codename = models.CharField(max_length=100, unique=True)

    # Version
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

    # States and transitions (JSON schema)
    states = models.JSONField(
        default=list,
        help_text='List of state definitions: [{name, label, is_initial, is_final}]'
    )
    transitions = models.JSONField(
        default=list,
        help_text='List of transition definitions: [{name, from_state, to_state, required_permissions}]'
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflow_definitions'
        verbose_name = 'Workflow Definition'
        verbose_name_plural = 'Workflow Definitions'
        ordering = ['name', '-version']
        indexes = [
            models.Index(fields=['codename', 'version']),
        ]

    def __str__(self):
        return f'{self.name} (v{self.version})'


class WorkflowInstance(models.Model):
    """
    Instance of a workflow execution.

    Key points:
    - Tracks current state of a workflow instance
    - Links to the entity being worked on
    - Audit trail of all state transitions
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Workflow definition
    workflow_definition = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name='instances'
    )

    # Entity being worked on (polymorphic)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()

    # Tenant context
    tenant = models.ForeignKey(
        'domain.Tenant',
        on_delete=models.CASCADE,
        related_name='workflow_instances'
    )

    # Current state
    current_state = models.CharField(max_length=100)

    # Status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_workflow_instances'
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'workflow_instances'
        verbose_name = 'Workflow Instance'
        verbose_name_plural = 'Workflow Instances'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['current_state']),
        ]

    def __str__(self):
        return f'{self.workflow_definition.name} - {self.entity_type}:{self.entity_id}'

    def transition_to(self, new_state, user, comment=''):
        """Transition to a new state."""
        from django.utils import timezone

        # Create transition log
        WorkflowTransition.objects.create(
            workflow_instance=self,
            from_state=self.current_state,
            to_state=new_state,
            performed_by=user,
            comment=comment
        )

        # Update current state
        self.current_state = new_state
        self.updated_at = timezone.now()

        # Check if this is a final state
        for state_def in self.workflow_definition.states:
            if state_def['name'] == new_state and state_def.get('is_final'):
                self.status = 'completed'
                self.completed_at = timezone.now()
                break

        self.save()


class WorkflowTransition(models.Model):
    """
    Audit log of workflow state transitions.

    Key points:
    - Immutable audit trail
    - Records from_state, to_state, performed_by, timestamp
    - Optional comment/reason
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Workflow instance
    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name='transitions'
    )

    # Transition details
    from_state = models.CharField(max_length=100)
    to_state = models.CharField(max_length=100)
    transition_name = models.CharField(max_length=100, blank=True)

    # Performed by
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_transitions'
    )

    # Comment
    comment = models.TextField(blank=True)

    # Timestamp
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workflow_transitions'
        verbose_name = 'Workflow Transition'
        verbose_name_plural = 'Workflow Transitions'
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['workflow_instance', 'performed_at']),
        ]

    def __str__(self):
        return f'{self.from_state} → {self.to_state} at {self.performed_at}'
