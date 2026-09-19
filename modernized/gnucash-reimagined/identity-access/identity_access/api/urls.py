"""
API URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, RefreshTokenView, MeView,
    TenantViewSet, MembershipViewSet, UserMembershipsViewSet,
    PracticeViewSet, ClientEngagementViewSet,
    NotificationViewSet, NotificationPreferenceViewSet
)

router = DefaultRouter()

# Tenants
router.register(r'tenants', TenantViewSet, basename='tenant')

# Practices
router.register(r'practices', PracticeViewSet, basename='practice')

# User memberships
router.register(r'memberships', UserMembershipsViewSet, basename='user-memberships')

# Notifications
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'notification-preferences', NotificationPreferenceViewSet, basename='notification-preference')

urlpatterns = [
    # Authentication
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='refresh-token'),
    path('auth/me/', MeView.as_view(), name='me'),

    # Router URLs
    path('', include(router.urls)),

    # Tenant memberships
    path(
        'tenants/<slug:tenant_slug>/members/',
        MembershipViewSet.as_view({'get': 'list'}),
        name='tenant-members'
    ),
    path(
        'tenants/<slug:tenant_slug>/members/invite/',
        MembershipViewSet.as_view({'post': 'invite'}),
        name='tenant-members-invite'
    ),
    path(
        'tenants/<slug:tenant_slug>/members/<uuid:pk>/update-role/',
        MembershipViewSet.as_view({'patch': 'update_role'}),
        name='tenant-member-update-role'
    ),
    path(
        'tenants/<slug:tenant_slug>/members/<uuid:pk>/remove/',
        MembershipViewSet.as_view({'delete': 'remove_member'}),
        name='tenant-member-remove'
    ),

    # Invitations
    path(
        'invitations/<str:token>/accept/',
        MembershipViewSet.as_view({'post': 'accept_invitation'}),
        name='accept-invitation'
    ),

    # Client engagements
    path(
        'engagements/<uuid:pk>/activate/',
        ClientEngagementViewSet.as_view({'post': 'activate'}),
        name='engagement-activate'
    ),
    path(
        'engagements/<uuid:pk>/terminate/',
        ClientEngagementViewSet.as_view({'post': 'terminate'}),
        name='engagement-terminate'
    ),
    path(
        'engagements/<uuid:pk>/access-grants/',
        ClientEngagementViewSet.as_view({'get': 'list_access_grants'}),
        name='engagement-access-grants'
    ),
    path(
        'engagements/<uuid:pk>/access-grants/grant/',
        ClientEngagementViewSet.as_view({'post': 'grant_access'}),
        name='engagement-grant-access'
    ),
    path(
        'engagements/<uuid:pk>/access-grants/<uuid:grant_guid>/revoke/',
        ClientEngagementViewSet.as_view({'post': 'revoke_access'}),
        name='engagement-revoke-access'
    ),
]
