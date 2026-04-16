from __future__ import annotations


class AccountError(Exception):
    pass


class AccountTypeChangeError(AccountError):
    pass
