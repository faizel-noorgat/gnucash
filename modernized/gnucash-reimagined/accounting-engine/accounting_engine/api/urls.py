"""
API URL configuration for accounting engine.

Implements REST API contracts from the specification.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"commodities", views.CommodityViewSet)
router.register(r"currencies", views.CommodityViewSet)  # Alias for currencies
router.register(r"exchange-rates", views.ExchangeRateViewSet)
router.register(r"accounts", views.AccountViewSet)
router.register(r"journal-entries", views.JournalEntryViewSet)
router.register(r"fiscal-periods", views.FiscalPeriodViewSet)
router.register(r"tax-rules", views.TaxRuleViewSet)
router.register(r"payment-terms", views.PaymentTermViewSet)
router.register(r"bank-accounts", views.BankAccountViewSet)
router.register(r"bank-transactions", views.BankTransactionViewSet)
router.register(r"bank-reconciliations", views.BankReconciliationViewSet)
router.register(r"intercompany-relationships", views.IntercompanyRelationshipViewSet)
router.register(r"intercompany-events", views.InterEntityEventViewSet)
router.register(r"lots", views.LotViewSet)
router.register(r"audit-events", views.AuditEventViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
