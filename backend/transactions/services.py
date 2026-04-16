from __future__ import annotations

from django.db import transaction


class TransactionService:
    @staticmethod
    @transaction.atomic
    def create(tenant, currency, post_date, description, splits, created_by=None, notes='', num=''):
        from transactions.models import Split, Transaction

        tx = Transaction.objects.create(
            tenant=tenant,
            currency=currency,
            post_date=post_date,
            description=description,
            notes=notes,
            num=num,
            created_by=created_by,
        )
        for split_data in splits:
            Split.objects.create(transaction=tx, **split_data)
        return tx
