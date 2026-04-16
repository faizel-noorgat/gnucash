from __future__ import annotations

from rest_framework import permissions

from tenants.models import TenantMembership


class IsTenantAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return TenantMembership.objects.filter(
            tenant__memberships__user=request.user,
            role__in=['OWNER', 'ADMIN'],
        ).exists()
