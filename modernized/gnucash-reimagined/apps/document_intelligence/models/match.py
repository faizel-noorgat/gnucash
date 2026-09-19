"""Document match model — links extracted documents to parties / invoices /
bank transactions.

A single document may have multiple candidate matches; at most one is
accepted. Rejected matches are preserved for audit.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class MatchKind(models.TextChoices):
    """What the document has been matched to."""

    PARTY = "party", "Matched to a Party (supplier / customer)"
    ACCOUNTING_DOCUMENT = "accounting_document", "Matched to an existing AccountingDocument"
    BANK_TRANSACTION = "bank_transaction", "Matched to a BankTransaction"
    DUPLICATE = "duplicate", "Identified as duplicate of another Document"


class MatchStatus(models.TextChoices):
    """Lifecycle of a single match candidate."""

    PROPOSED = "proposed", "Proposed by the matching pipeline"
    ACCEPTED = "accepted", "Accepted (manually or automatically)"
    REJECTED = "rejected", "Explicitly rejected by reviewer"
    SUPERSEDED = "superseded", "Superseded by a later match"


class DocumentMatch(models.Model):
    """A candidate match between a document and an external entity."""

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "document_intelligence.Document",
        on_delete=models.CASCADE,
        related_name="matches",
    )
    extraction = models.ForeignKey(
        "document_intelligence.DocumentExtraction",
        on_delete=models.CASCADE,
        related_name="matches",
        null=True,
        blank=True,
    )

    kind = models.CharField(max_length=32, choices=MatchKind.choices)
    status = models.CharField(
        max_length=32,
        choices=MatchStatus.choices,
        default=MatchStatus.PROPOSED,
        db_index=True,
    )

    # Polymorphic target — only one of these is populated, per `kind`
    target_party_id = models.UUIDField(null=True, blank=True, db_index=True)
    target_accounting_document_id = models.UUIDField(null=True, blank=True, db_index=True)
    target_bank_transaction_id = models.UUIDField(null=True, blank=True, db_index=True)
    target_document_id = models.UUIDField(null=True, blank=True, db_index=True)  # duplicate

    # Provenance
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    evidence = models.JSONField(default=dict)

    # Actor
    decided_by = models.UUIDField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "document_intelligence"
        db_table = "document_matches"
        ordering = ["-confidence", "-created_at"]
        constraints = [
            # At most one ACCEPTED match per (document, kind) at any moment
            models.UniqueConstraint(
                fields=["document", "kind"],
                condition=models.Q(status="accepted"),
                name="uniq_accepted_match_per_document_kind",
            ),
        ]

    def accept(self, user_id: uuid.UUID | None) -> None:
        """Accept this match, superseding any other accepted match of the same kind."""
        # Reject competing matches of the same kind for this document
        type(self).objects.filter(
            document=self.document,
            kind=self.kind,
            status=MatchStatus.ACCEPTED,
        ).exclude(pk=self.pk).update(
            status=MatchStatus.SUPERSEDED,
            decided_by=user_id,
            decided_at=timezone.now(),
        )
        self.status = MatchStatus.ACCEPTED
        self.decided_by = user_id
        self.decided_at = timezone.now()
        self.save()

    def reject(self, user_id: uuid.UUID | None) -> None:
        """Reject this match."""
        self.status = MatchStatus.REJECTED
        self.decided_by = user_id
        self.decided_at = timezone.now()
        self.save()

    def __str__(self) -> str:
        return f"Match {self.guid} ({self.kind}: {self.status})"
