"""
Permission domain model.

Represents granular access control permissions.
"""
import uuid
from django.db import models


class Permission(models.Model):
    """
    Granular permission for access control.

    Key points:
    - Codename format: 'action_resource' (e.g., 'create_invoice', 'view_report')
    - Can be assigned to roles
    - System permissions are predefined and cannot be modified
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic information
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Category
    CATEGORY_CHOICES = [
        ('accounting', 'Accounting'),
        ('banking', 'Banking'),
        ('documents', 'Documents'),
        ('reports', 'Reports'),
        ('admin', 'Administration'),
        ('settings', 'Settings'),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='accounting')

    # System permissions are predefined and cannot be modified
    is_system_permission = models.BooleanField(default=False)

    # Status
    is_active = models.BooleanField(default=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        ordering = ['category', 'codename']
        indexes = [
            models.Index(fields=['codename']),
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return f'{self.codename} - {self.name}'
