"""
URL configuration for accounting API.

Defines URL patterns for all accounting endpoints.

API Endpoints:
    Commodities:
        GET    /api/accounting/commodities/          - List commodities
        POST   /api/accounting/commodities/          - Create commodity
        GET    /api/accounting/commodities/{guid}/   - Retrieve commodity
        PUT    /api/accounting/commodities/{guid}/   - Update commodity
        DELETE /api/accounting/commodities/{guid}/   - Delete commodity

    Accounts:
        GET    /api/accounting/accounts/             - List accounts
        POST   /api/accounting/accounts/             - Create account
        GET    /api/accounting/accounts/{guid}/      - Retrieve account
        PUT    /api/accounting/accounts/{guid}/      - Update account
        DELETE /api/accounting/accounts/{guid}/      - Delete account
        GET    /api/accounting/accounts/{guid}/balance/ - Get account balance

    Journal Entries:
        GET    /api/accounting/journal-entries/      - List journal entries
        POST   /api/accounting/journal-entries/      - Create journal entry
        GET    /api/accounting/journal-entries/{guid}/ - Retrieve journal entry
        PUT    /api/accounting/journal-entries/{guid}/ - Update journal entry
        POST   /api/accounting/journal-entries/{guid}/post/ - Post journal entry
        POST   /api/accounting/journal-entries/{guid}/reverse/ - Reverse journal entry
        POST   /api/accounting/journal-entries/{guid}/void/   - Void journal entry

    Journal Lines:
        GET    /api/accounting/journal-lines/        - List journal lines
        POST   /api/accounting/journal-lines/        - Create journal line
        GET    /api/accounting/journal-lines/{guid}/ - Retrieve journal line
        PUT    /api/accounting/journal-lines/{guid}/ - Update journal line
        DELETE /api/accounting/journal-lines/{guid}/ - Delete journal line

    Lots:
        GET    /api/accounting/lots/                 - List lots
        POST   /api/accounting/lots/                 - Create lot
        GET    /api/accounting/lots/{guid}/          - Retrieve lot
        GET    /api/accounting/lots/{guid}/balance/  - Get lot balance

    Fiscal Periods:
        GET    /api/accounting/fiscal-periods/       - List fiscal periods
        POST   /api/accounting/fiscal-periods/       - Create fiscal period
        GET    /api/accounting/fiscal-periods/{guid}/ - Retrieve fiscal period
        POST   /api/accounting/fiscal-periods/{guid}/close/ - Close period
        POST   /api/accounting/fiscal-periods/{guid}/lock/  - Lock period
        POST   /api/accounting/fiscal-periods/{guid}/reopen/ - Reopen period

    Tax Rules:
        GET    /api/accounting/tax-rules/            - List tax rules
        POST   /api/accounting/tax-rules/            - Create tax rule
        GET    /api/accounting/tax-rules/{guid}/     - Retrieve tax rule
        PUT    /api/accounting/tax-rules/{guid}/     - Update tax rule

    Payment Terms:
        GET    /api/accounting/payment-terms/        - List payment terms
        POST   /api/accounting/payment-terms/        - Create payment term
        GET    /api/accounting/payment-terms/{guid}/ - Retrieve payment term
        PUT    /api/accounting/payment-terms/{guid}/ - Update payment term

    Bank Accounts:
        GET    /api/accounting/bank-accounts/        - List bank accounts
        POST   /api/accounting/bank-accounts/        - Create bank account
        GET    /api/accounting/bank-accounts/{guid}/ - Retrieve bank account
        PUT    /api/accounting/bank-accounts/{guid}/ - Update bank account

    Bank Statements:
        GET    /api/accounting/bank-statements/      - List bank statements
        POST   /api/accounting/bank-statements/      - Import bank statement
        GET    /api/accounting/bank-statements/{guid}/ - Retrieve bank statement

    Reconciliations:
        GET    /api/accounting/reconciliations/      - List reconciliations
        POST   /api/accounting/reconciliations/      - Start reconciliation
        GET    /api/accounting/reconciliations/{guid}/ - Retrieve reconciliation
        POST   /api/accounting/reconciliations/{guid}/complete/ - Complete reconciliation

    Intercompany:
        GET    /api/accounting/intercompany/relationships/ - List relationships
        POST   /api/accounting/intercompany/relationships/ - Create relationship
        GET    /api/accounting/intercompany/events/  - List intercompany events
        POST   /api/accounting/intercompany/events/  - Propose intercompany event
        POST   /api/accounting/intercompany/events/{guid}/accept/ - Accept event
        POST   /api/accounting/intercompany/events/{guid}/reject/ - Reject event

    Audit Events:
        GET    /api/accounting/audit-events/         - List audit events (read-only)
        GET    /api/accounting/audit-events/{guid}/  - Retrieve audit event (read-only)
"""

from django.urls import path

from . import views

app_name = "accounting"

urlpatterns = [
    # Commodities
    path(
        "commodities/",
        views.CommodityListCreateView.as_view(),
        name="commodity-list",
    ),
    path(
        "commodities/<uuid:guid>/",
        views.CommodityRetrieveUpdateDestroyView.as_view(),
        name="commodity-detail",
    ),

    # Accounts
    path(
        "accounts/",
        views.AccountListCreateView.as_view(),
        name="account-list",
    ),
    path(
        "accounts/<uuid:guid>/",
        views.AccountRetrieveUpdateDestroyView.as_view(),
        name="account-detail",
    ),
    path(
        "accounts/<uuid:guid>/balance/",
        views.AccountBalanceView.as_view(),
        name="account-balance",
    ),

    # Journal Entries
    path(
        "journal-entries/",
        views.JournalEntryListCreateView.as_view(),
        name="journal-entry-list",
    ),
    path(
        "journal-entries/<uuid:guid>/",
        views.JournalEntryRetrieveUpdateView.as_view(),
        name="journal-entry-detail",
    ),
    path(
        "journal-entries/<uuid:guid>/post/",
        views.JournalEntryPostView.as_view(),
        name="journal-entry-post",
    ),
    path(
        "journal-entries/<uuid:guid>/reverse/",
        views.JournalEntryReverseView.as_view(),
        name="journal-entry-reverse",
    ),
    path(
        "journal-entries/<uuid:guid>/void/",
        views.JournalEntryVoidView.as_view(),
        name="journal-entry-void",
    ),

    # Journal Lines
    path(
        "journal-lines/",
        views.JournalLineListCreateView.as_view(),
        name="journal-line-list",
    ),
    path(
        "journal-lines/<uuid:guid>/",
        views.JournalLineRetrieveUpdateDestroyView.as_view(),
        name="journal-line-detail",
    ),

    # Lots
    path(
        "lots/",
        views.LotListCreateView.as_view(),
        name="lot-list",
    ),
    path(
        "lots/<uuid:guid>/",
        views.LotRetrieveView.as_view(),
        name="lot-detail",
    ),
    path(
        "lots/<uuid:guid>/balance/",
        views.LotBalanceView.as_view(),
        name="lot-balance",
    ),

    # Fiscal Periods
    path(
        "fiscal-periods/",
        views.FiscalPeriodListCreateView.as_view(),
        name="fiscal-period-list",
    ),
    path(
        "fiscal-periods/<uuid:guid>/",
        views.FiscalPeriodRetrieveView.as_view(),
        name="fiscal-period-detail",
    ),
    path(
        "fiscal-periods/<uuid:guid>/close/",
        views.FiscalPeriodCloseView.as_view(),
        name="fiscal-period-close",
    ),
    path(
        "fiscal-periods/<uuid:guid>/lock/",
        views.FiscalPeriodLockView.as_view(),
        name="fiscal-period-lock",
    ),
    path(
        "fiscal-periods/<uuid:guid>/reopen/",
        views.FiscalPeriodReopenView.as_view(),
        name="fiscal-period-reopen",
    ),

    # Tax Rules
    path(
        "tax-rules/",
        views.TaxRuleListCreateView.as_view(),
        name="tax-rule-list",
    ),
    path(
        "tax-rules/<uuid:guid>/",
        views.TaxRuleRetrieveUpdateView.as_view(),
        name="tax-rule-detail",
    ),

    # Payment Terms
    path(
        "payment-terms/",
        views.PaymentTermListCreateView.as_view(),
        name="payment-term-list",
    ),
    path(
        "payment-terms/<uuid:guid>/",
        views.PaymentTermRetrieveUpdateView.as_view(),
        name="payment-term-detail",
    ),

    # Bank Accounts
    path(
        "bank-accounts/",
        views.BankAccountListCreateView.as_view(),
        name="bank-account-list",
    ),
    path(
        "bank-accounts/<uuid:guid>/",
        views.BankAccountRetrieveUpdateView.as_view(),
        name="bank-account-detail",
    ),

    # Bank Statements
    path(
        "bank-statements/",
        views.BankStatementListCreateView.as_view(),
        name="bank-statement-list",
    ),
    path(
        "bank-statements/<uuid:guid>/",
        views.BankStatementRetrieveView.as_view(),
        name="bank-statement-detail",
    ),

    # Reconciliations
    path(
        "reconciliations/",
        views.ReconciliationListCreateView.as_view(),
        name="reconciliation-list",
    ),
    path(
        "reconciliations/<uuid:guid>/",
        views.ReconciliationRetrieveView.as_view(),
        name="reconciliation-detail",
    ),
    path(
        "reconciliations/<uuid:guid>/complete/",
        views.ReconciliationCompleteView.as_view(),
        name="reconciliation-complete",
    ),

    # Intercompany
    path(
        "intercompany/relationships/",
        views.IntercompanyRelationshipListCreateView.as_view(),
        name="intercompany-relationship-list",
    ),
    path(
        "intercompany/events/",
        views.InterEntityEventListCreateView.as_view(),
        name="intercompany-event-list",
    ),
    path(
        "intercompany/events/<uuid:guid>/accept/",
        views.InterEntityEventAcceptView.as_view(),
        name="intercompany-event-accept",
    ),
    path(
        "intercompany/events/<uuid:guid>/reject/",
        views.InterEntityEventRejectView.as_view(),
        name="intercompany-event-reject",
    ),

    # Audit Events (read-only)
    path(
        "audit-events/",
        views.AuditEventListView.as_view(),
        name="audit-event-list",
    ),
    path(
        "audit-events/<uuid:guid>/",
        views.AuditEventDetailView.as_view(),
        name="audit-event-detail",
    ),
]
