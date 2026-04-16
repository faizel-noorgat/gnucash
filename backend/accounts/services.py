from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import F, Prefetch, Sum

if TYPE_CHECKING:
    from accounts.models import Account
    from transactions.models import Split, Transaction


def get_account_register(
    account: Account,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Return register data for a single account: all splits touching this account
    with transaction context, other account names, and running balance.
    """
    from transactions.models import Split, Transaction

    qs = (
        Split.objects
        .filter(account=account, tenant=account.tenant)
        .select_related('transaction', 'transaction__currency')
        .prefetch_related(
            Prefetch(
                'transaction__splits',
                queryset=Split.objects.select_related('account').exclude(account=account),
                to_attr='other_splits',
            )
        )
        .order_by('transaction__post_date', 'transaction__enter_date', 'id')
    )

    if start_date:
        qs = qs.filter(transaction__post_date__gte=start_date)
    if end_date:
        qs = qs.filter(transaction__post_date__lte=end_date)

    splits: list[Split] = list(qs)

    entries = []
    running_balance = Decimal('0')

    for split in splits:
        running_balance += split.value
        other_accounts = [
            s.account.full_name or s.account.name
            for s in getattr(split, 'other_splits', [])
        ]
        entries.append({
            'id': split.id,
            'post_date': split.transaction.post_date,
            'description': split.transaction.description,
            'num': split.transaction.num,
            'split_value': str(split.value),
            'split_memo': split.memo,
            'other_accounts': other_accounts,
            'reconcile_state': split.reconcile_state,
            'created_at': split.created_at,
        })

    return {
        'account': account,
        'transactions': entries,
        'running_balance': str(running_balance),
    }
