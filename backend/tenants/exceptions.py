from __future__ import annotations


class TenantError(Exception):
    pass


class TenantNotFoundError(TenantError):
    pass


class TenantAccessDenied(TenantError):
    pass
