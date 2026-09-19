"""
Identity & Access Domain Models Package

Exports all domain models for the Identity & Access bounded context.
All models are organized under the `identity` Django app label.
"""

from .user import User
from .tenant import Tenant, LegalEntity
from .membership import Membership, Role, RolePermission, Permission
from .practice import Practice, PracticeMembership, ClientEngagement, AdvisorAccessGrant
from .notification import (
    Notification,
    NotificationPreference,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowTransition,
)
from .api_token import ApiToken

__all__ = [
    # Core identity
    'User',
    'Tenant',
    'LegalEntity',

    # Membership and access
    'Membership',
    'Role',
    'RolePermission',
    'Permission',
    'ApiToken',

    # Practice/Advisor access
    'Practice',
    'PracticeMembership',
    'ClientEngagement',
    'AdvisorAccessGrant',

    # Notifications
    'Notification',
    'NotificationPreference',

    # Workflows
    'WorkflowDefinition',
    'WorkflowInstance',
    'WorkflowTransition',
]
