"""
API views for accounting engine.

Implements REST API contracts from the specification.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from accounting_engine.models import (
    Account,
    AuditEvent,
    BankAccount,
    BankReconciliation,
    BankStatement,
    BankTransaction,
    Commodity,
    ExchangeRate,
    FiscalPeriod,
    InterEntityEvent,
    IntercompanyRelationship,
    JournalEntry,
    Lot,
    PaymentTerm,
    TaxRule,
)
from .serializers import (
    AccountSerializer,
    AuditEventSerializer,
    BankAccountSerializer,
    BankReconciliationSerializer,
    BankStatementSerializer,
    BankTransactionSerializer,
    CommoditySerializer,
    ExchangeRateSerializer,
    FiscalPeriodSerializer,
    InterEntityEventSerializer,
    IntercompanyRelationshipSerializer,
    JournalEntrySerializer,
    JournalEntryCreateSerializer,
    LotSerializer,
    PaymentTermSerializer,
    TaxRuleSerializer,
)


class CommodityViewSet(viewsets.ModelViewSet):
    """API endpoint for commodities."""

    serializer_class = CommoditySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["namespace", "mnemonic"]
    search_fields = ["mnemonic", "fullname"]

    def get_queryset(self):
        return Commodity.objects.filter(tenant=self.request.user.tenant)


class ExchangeRateViewSet(viewsets.ModelViewSet):
    """API endpoint for exchange rates."""

    serializer_class = ExchangeRateSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["from_commodity", "to_commodity", "rate_date"]
    ordering_fields = ["rate_date"]
    ordering = ["-rate_date"]

    def get_queryset(self):
        return ExchangeRate.objects.filter(tenant=self.request.user.tenant)


class AccountViewSet(viewsets.ModelViewSet):
    """
    API endpoint for accounts (chart of accounts).

    Implements hierarchical account management with fundamental type detection.
    """

    serializer_class = AccountSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["account_type", "parent", "is_placeholder", "is_system", "legal_entity"]
    search_fields = ["name", "code", "description"]
    ordering_fields = ["code", "name", "path"]
    ordering = ["path"]

    def get_queryset(self):
        return Account.objects.filter(tenant=self.request.user.tenant)

    @action(detail=True, methods=["get"])
    def balance(self, request, pk=None):
        """Get account balance."""
        account = self.get_object()
        as_of_date = request.query_params.get("as_of_date")
        balance = account.get_balance(as_of_date)
        return Response({"balance": str(balance)})

    @action(detail=True, methods=["get"])
    def reconciled_balance(self, request, pk=None):
        """Get reconciled balance (BR-SPLIT-004)."""
        account = self.get_object()
        as_of_date = request.query_params.get("as_of_date")
        balance = account.get_reconciled_balance(as_of_date)
        return Response({"reconciled_balance": str(balance)})


class JournalEntryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for journal entries.

    Implements double-entry accounting with posting workflow.
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "is_posted", "legal_entity", "date"]
    search_fields = ["description", "reference", "num"]
    ordering_fields = ["date", "date_entered"]
    ordering = ["-date", "-date_entered"]

    def get_queryset(self):
        return JournalEntry.objects.filter(tenant=self.request.user.tenant)

    def get_serializer_class(self):
        if self.action == "create":
            return JournalEntryCreateSerializer
        return JournalEntrySerializer

    @action(detail=True, methods=["post"])
    def post_entry(self, request, pk=None):
        """Post a journal entry (make it immutable)."""
        journal_entry = self.get_object()
        try:
            journal_entry.post(user=request.user)
            return Response(
                JournalEntrySerializer(journal_entry).data,
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        """Create a reversal entry for a posted journal."""
        journal_entry = self.get_object()
        description = request.data.get("description")
        try:
            reversal = journal_entry.create_reversal(
                user=request.user,
                description=description,
            )
            return Response(
                JournalEntrySerializer(reversal).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def correct(self, request, pk=None):
        """Create a correcting entry for a posted journal."""
        journal_entry = self.get_object()
        corrections = request.data.get("corrections", {})
        try:
            correction = journal_entry.create_correcting_entry(
                corrections=corrections,
                user=request.user,
            )
            return Response(
                JournalEntrySerializer(correction).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FiscalPeriodViewSet(viewsets.ModelViewSet):
    """API endpoint for fiscal periods."""

    serializer_class = FiscalPeriodSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "fiscal_year", "legal_entity"]
    ordering_fields = ["start_date", "end_date"]
    ordering = ["-start_date"]

    def get_queryset(self):
        return FiscalPeriod.objects.filter(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Close a fiscal period."""
        period = self.get_object()
        try:
            period.close(user=request.user)
            return Response(FiscalPeriodSerializer(period).data)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        """Lock a fiscal period (permanent)."""
        period = self.get_object()
        period.lock(user=request.user)
        return Response(FiscalPeriodSerializer(period).data)


class TaxRuleViewSet(viewsets.ModelViewSet):
    """API endpoint for tax rules."""

    serializer_class = TaxRuleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["code", "rule_type", "is_active"]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return TaxRule.objects.filter(tenant=self.request.user.tenant)


class PaymentTermViewSet(viewsets.ModelViewSet):
    """API endpoint for payment terms."""

    serializer_class = PaymentTermSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        return PaymentTerm.objects.filter(tenant=self.request.user.tenant)


class BankAccountViewSet(viewsets.ModelViewSet):
    """API endpoint for bank accounts."""

    serializer_class = BankAccountSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active", "legal_entity"]
    search_fields = ["bank_name", "account_number"]

    def get_queryset(self):
        return BankAccount.objects.filter(tenant=self.request.user.tenant)


class BankTransactionViewSet(viewsets.ModelViewSet):
    """API endpoint for bank transactions."""

    serializer_class = BankTransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["statement", "match_status"]
    ordering_fields = ["transaction_date"]
    ordering = ["-transaction_date"]

    def get_queryset(self):
        return BankTransaction.objects.filter(tenant=self.request.user.tenant)


class BankReconciliationViewSet(viewsets.ModelViewSet):
    """API endpoint for bank reconciliations."""

    serializer_class = BankReconciliationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["bank_account", "status"]
    ordering_fields = ["started_at"]
    ordering = ["-started_at"]

    def get_queryset(self):
        return BankReconciliation.objects.filter(tenant=self.request.user.tenant)


class IntercompanyRelationshipViewSet(viewsets.ModelViewSet):
    """API endpoint for intercompany relationships."""

    serializer_class = IntercompanyRelationshipSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["entity_a", "entity_b", "is_active"]

    def get_queryset(self):
        return IntercompanyRelationship.objects.filter(tenant=self.request.user.tenant)


class InterEntityEventViewSet(viewsets.ModelViewSet):
    """API endpoint for intercompany events."""

    serializer_class = InterEntityEventSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "source_entity", "counterparty_entity"]
    ordering_fields = ["proposed_at"]
    ordering = ["-proposed_at"]

    def get_queryset(self):
        return InterEntityEvent.objects.filter(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Accept an intercompany event."""
        event = self.get_object()
        event.accept(user=request.user)
        return Response(InterEntityEventSerializer(event).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject an intercompany event."""
        event = self.get_object()
        reason = request.data.get("reason", "")
        event.reject(user=request.user, reason=reason)
        return Response(InterEntityEventSerializer(event).data)


class LotViewSet(viewsets.ModelViewSet):
    """API endpoint for lots (inventory/stock tracking)."""

    serializer_class = LotSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["account", "is_closed"]

    def get_queryset(self):
        return Lot.objects.filter(tenant=self.request.user.tenant)


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for audit events (read-only)."""

    serializer_class = AuditEventSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["action", "entity_type", "actor"]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]

    def get_queryset(self):
        return AuditEvent.objects.filter(tenant=self.request.user.tenant)
