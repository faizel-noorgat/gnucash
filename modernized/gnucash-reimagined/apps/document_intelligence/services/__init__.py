"""Services for Document Intelligence bounded context.

Services orchestrate business logic and coordinate between models and
external providers (OCR, AI, storage).

Key services:
- OCRService: Calls external OCR provider (AWS Textract, Google Document AI, etc.)
- ExtractionService: Structured extraction from OCR results
- MatchingService: Supplier/customer/bank transaction matching
- MappingService: Learned accounting mappings management
- SuggestionService: AI-generated suggestions with confidence scores

Design principles:
- AI/OCR outputs NEVER directly post journals - they propose, deterministic
  services post (separation of concerns, auditability)
- All mutations preserve append-only audit trail (BR-DI-003, BR-DI-004, BR-DI-009)
- Tenant-scoped via tenant_id parameter (BR-DI-010)
- Full provenance captured for all AI/OCR decisions (BR-DI-008)
"""

from __future__ import annotations

__all__ = [
    "OCRService",
    "ExtractionService",
    "MatchingService",
    "MappingService",
    "SuggestionService",
]
