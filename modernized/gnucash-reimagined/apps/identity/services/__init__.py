"""
Identity Services Package

Domain services for the Identity & Access bounded context.
These services encapsulate business logic that spans multiple models
and orchestrates domain operations.

AuthenticationService:
    - Login/logout, session management
    - Token-based authentication and validation
    - Password reset, MFA verification

AuthorizationService:
    - Permission and role checks across tenants and entities
    - Tenant membership and accessible-tenant resolution
    - Advisor access evaluation

TenantService:
    - Tenant lifecycle and onboarding
    - Legal entity creation within a tenant
    - Tenant member invitation and context resolution

MembershipService:
    - User invitation to a tenant
    - Accepting invitations and role updates
    - Removing members from a tenant

PracticeService:
    - Practice and practice-membership management
    - Client engagements between practice and tenant
    - Advisor access grants

NotificationService:
    - Notification creation and email delivery
    - Read/unread tracking
    - Per-user notification preferences
"""

from .authentication import AuthenticationService
from .authorization import AuthorizationService
from .membership import MembershipService
from .notification import NotificationService
from .practice import PracticeService
from .tenant_service import TenantService

__all__ = [
    "AuthenticationService",
    "AuthorizationService",
    "TenantService",
    "MembershipService",
    "PracticeService",
    "NotificationService",
]
