from __future__ import annotations

from django.db import connection

from tenants.models import TenantMembership


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            tenant_id = request.headers.get('X-Tenant-ID')
            if tenant_id:
                try:
                    membership = TenantMembership.objects.select_related('tenant').get(
                        tenant_id=tenant_id, user=request.user
                    )
                    request.tenant = membership.tenant
                    connection.cursor().execute(
                        "SET app.current_tenant = %s", [str(tenant_id)]
                    )
                except TenantMembership.DoesNotExist:
                    pass
        return self.get_response(request)
