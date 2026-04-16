# backend/admin_api/permissions.py
from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    """
    Allow access only to users with is_staff=True.
    This permission is used for all cross-tenant admin endpoints.
    """

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
