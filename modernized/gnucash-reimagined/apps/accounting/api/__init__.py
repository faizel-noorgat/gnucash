"""
API package for accounting app.

This package contains the REST API for the accounting bounded context:

URLs:
    - /api/accounting/commodities/ - Commodity CRUD
    - /api/accounting/accounts/ - Account CRUD
    - /api/accounting/journal-entries/ - Journal entry operations
    - /api/accounting/journal-lines/ - Journal line operations
    - /api/accounting/lots/ - Lot operations
    - /api/accounting/fiscal-periods/ - Fiscal period management
    - /api/accounting/tax-rules/ - Tax rule management
    - /api/accounting/payment-terms/ - Payment term management
    - /api/accounting/bank-accounts/ - Bank account management
    - /api/accounting/bank-statements/ - Bank statement import
    - /api/accounting/reconciliations/ - Bank reconciliation
    - /api/accounting/intercompany/ - Intercompany transactions
    - /api/accounting/audit-events/ - Audit trail (read-only)

API Design:
    - RESTful endpoints following Django REST Framework conventions
    - Tenant-scoped queries (multi-tenancy)
    - Idempotency keys for POST operations
    - Comprehensive error handling
    - Pagination for list endpoints
"""
