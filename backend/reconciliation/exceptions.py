from __future__ import annotations


class ReconciliationError(Exception):
    pass


class BalanceMismatchError(ReconciliationError):
    pass
