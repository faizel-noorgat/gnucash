from __future__ import annotations


class TransactionError(Exception):
    pass


class UnbalancedTransactionError(TransactionError):
    pass
