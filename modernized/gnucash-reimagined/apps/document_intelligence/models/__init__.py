"""Domain models for Document Intelligence.

Re-exports each model for convenient `from apps.document_intelligence.models import ...`.

Models are organized by responsibility:
- document: Document (uploaded file with provenance)
- extraction: DocumentExtraction (OCR results with version history)
- match: DocumentMatch (matched to Party/Document/BankTransaction)
- mapping: AccountingMapping (learned organizational rules)
- suggestion: MappingSuggestion (AI-generated suggestions with confidence)
- review: ReviewQueue, ReviewDecisionLog (human review workflow)
"""

from .document import Document, DocumentSource, DocumentStatus
from .extraction import (
    DocumentExtraction,
    ExtractionStatus,
    ExtractionVersion,
)
from .mapping import AccountingMapping, MappingConfidence
from .match import DocumentMatch, MatchKind, MatchStatus
from .review import ReviewDecision, ReviewDecisionLog, ReviewQueue, ReviewStatus
from .suggestion import MappingSuggestion

__all__ = [
    # document
    "Document",
    "DocumentSource",
    "DocumentStatus",
    # extraction
    "DocumentExtraction",
    "ExtractionStatus",
    "ExtractionVersion",
    # match
    "DocumentMatch",
    "MatchKind",
    "MatchStatus",
    # mapping
    "AccountingMapping",
    "MappingConfidence",
    # suggestion
    "MappingSuggestion",
    # review
    "ReviewQueue",
    "ReviewStatus",
    "ReviewDecision",
    "ReviewDecisionLog",
]
