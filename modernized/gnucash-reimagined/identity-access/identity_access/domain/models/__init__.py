"""
Domain Models Package

Exports all domain models for the Identity & Access bounded context.
"""

from .user import User
from .tenant import Tenant
from .legal_entity import LegalEntity
from .membership import Membership
from .role import Role, RolePermission
from .permission import Permission
from .api_token import ApiToken
from .practice import Practice
from .practice_membership import PracticeMembership
from .client_engagement import ClientEngagement
from .advisor_access_grant import AdvisorAccessGrant
from .notification import Notification, NotificationPreference
from .workflow_state import WorkflowDefinition, WorkflowInstance, WorkflowTransition

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
