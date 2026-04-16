from __future__ import annotations

from django.db import connection

from tenants.models import TenantMembership


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = request.headers.get('X-Tenant-ID')
        if tenant_id:
            try:
                from tenants.models import Tenant

                tenant = Tenant.objects.get(id=tenant_id)
                request.tenant = tenant
                connection.cursor().execute(
                    "SET app.current_tenant = %s", [str(tenant_id)]
                )
            except Exception:
                pass
        return self.get_response(request)
