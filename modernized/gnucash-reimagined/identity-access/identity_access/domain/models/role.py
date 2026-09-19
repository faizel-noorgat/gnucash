"""
Role domain model.

Represents workspace-level and entity-level permissions.
"""
import uuid
from django.db import models


class Role(models.Model):
    """
    Role with workspace-level and entity-scoped permissions.

    Key points:
    - Can be tenant-wide or scoped to specific legal entity
    - Defines set of permissions
    - Used in Membership and AdvisorAccessGrant
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic information
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Scope
    tenant = models.ForeignKey(
        'domain.Tenant',
        on_delete=models.CASCADE,
        related_name='roles',
        null=True,
        blank=True
    )

    # System roles are predefined and cannot be modified
    is_system_role = models.BooleanField(default=False)

    # Status
    is_active = models.BooleanField(default=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        if self.tenant:
            return f'{self.name} ({self.tenant.name})'
        return self.name

    def get_permissions(self):
        """Get all permissions for this role."""
        return self.permissions.filter(is_active=True)


class RolePermission(models.Model):
    """
    Many-to-many relationship between Role and Permission.
    """

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    permission = models.ForeignKey(
        'domain.Permission',
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )

    class Meta:
        db_table = 'role_permissions'
        unique_together = [['role', 'permission']]
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'

    def __str__(self):
        return f'{self.role.name} - {self.permission.codename}'
