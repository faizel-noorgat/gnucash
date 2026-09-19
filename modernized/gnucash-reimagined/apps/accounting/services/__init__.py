"""
Services package for accounting app.

This package contains business logic services for accounting operations:

PostingService:
    - Handles journal entry posting with ACID compliance
    - Validates double-entry balance (BR-ACCT-001, BR-ACCT-002)
    - Checks fiscal period status
    - Enforces idempotency keys
    - Creates immutable audit trail

ReversalService:
    - Creates reversal entries for posted journals
    - Creates correcting entries for differences
    - Handles void operations

FXService:
    - Exchange rate lookups (nearest-in-time)
    - Currency conversions
    - Multi-currency transaction validation
"""

from .fx import FXService
from .posting import PostingService
from .reversal import ReversalService

__all__ = [
    "PostingService",
    "ReversalService",
    "FXService",
]
