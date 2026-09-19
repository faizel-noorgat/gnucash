"""Domain models for Document Intelligence.

Re-exports each model for convenient `from document_intelligence.models import ...`.
"""

from .document import Document, DocumentSource, DocumentStatus
from .extraction import (
    DocumentExtraction,
    ExtractionStatus,
    ExtractionVersion,
)
from .match import DocumentMatch, MatchKind, MatchStatus
from .mapping import AccountingMapping, MappingSuggestion, MappingConfidence
from .review import ReviewQueue, ReviewStatus

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
    "MappingSuggestion",
    "MappingConfidence",
    # review
    "ReviewQueue",
    "ReviewStatus",
]
