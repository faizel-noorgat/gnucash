"""
Middleware for tenant context management
"""
from django.conf import settings
from django.http import HttpResponseForbidden
import threading


# Thread-local storage for tenant context
_tenant_context = threading.local()


def get_current_tenant_id():
    """Get current tenant ID from thread-local storage"""
    return getattr(_tenant_context, 'tenant_id', None)


def get_current_legal_entity_id():
    """Get current legal entity ID from thread-local storage"""
    return getattr(_tenant_context, 'legal_entity_id', None)


class TenantContextMiddleware:
    """
    Middleware to extract tenant context from request headers.

    Sets tenant_id and legal_entity_id on request object for use in views.
    Also sets thread-local context for use in models and services.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.tenant_header = getattr(settings, 'TENANT_CONTEXT_HEADER', 'X-Tenant-ID')

    def __call__(self, request):
        # Extract tenant ID from header
        tenant_id = request.headers.get(self.tenant_header)

        if not tenant_id:
            # For now, allow requests without tenant ID (will be enforced later)
            # In production, this should return HttpResponseForbidden
            pass

        # Extract legal entity ID from header (optional)
        legal_entity_id = request.headers.get('X-Legal-Entity-ID')

        # Set on request object
        request.tenant_id = tenant_id
        request.legal_entity_id = legal_entity_id

        # Set thread-local context
        _tenant_context.tenant_id = tenant_id
        _tenant_context.legal_entity_id = legal_entity_id

        try:
            response = self.get_response(request)
        finally:
            # Clear thread-local context
            _tenant_context.tenant_id = None
            _tenant_context.legal_entity_id = None

        return response
