"""
Membership, Role, and Permission domain models.

Represents user ↔ tenant relationships with roles and granular permissions
for access control.
"""
import uuid
from django.db import models
from django.conf import settings


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
        'identity.Tenant',
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
        Permission,
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


class Membership(models.Model):
    """
    User membership in a tenant with specific role(s).

    Key points:
    - Links users to tenants
    - Can have multiple memberships (user in multiple tenants)
    - Each membership has a role that determines permissions
    - Invitation workflow for adding new members
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    tenant = models.ForeignKey(
        'identity.Tenant',
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    # Role
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Administrator'),
        ('accountant', 'Accountant'),
        ('bookkeeper', 'Bookkeeper'),
        ('ap_clerk', 'AP Clerk'),
        ('ar_clerk', 'AR Clerk'),
        ('approver', 'Approver'),
        ('auditor', 'Auditor'),
        ('viewer', 'Viewer'),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='viewer')

    # Status
    STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('deactivated', 'Deactivated'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')

    # Invitation
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations'
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    invitation_token = models.CharField(max_length=100, unique=True, null=True, blank=True)

    # Entity scope (optional - if None, role applies to all entities in tenant)
    scoped_entity = models.ForeignKey(
        'identity.LegalEntity',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='scoped_memberships'
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'memberships'
        verbose_name = 'Membership'
        verbose_name_plural = 'Memberships'
        unique_together = [['user', 'tenant', 'scoped_entity']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'tenant']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['invitation_token']),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.tenant.name} ({self.get_role_display()})'

    @property
    def is_active(self):
        """Check if membership is active."""
        return self.status == 'active'

    def accept_invitation(self):
        """Accept the membership invitation."""
        from django.utils import timezone
        self.status = 'active'
        self.accepted_at = timezone.now()
        self.save()
