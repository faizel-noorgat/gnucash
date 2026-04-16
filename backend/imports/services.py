from __future__ import annotations

import csv
import io
from decimal import Decimal
from django.db import transaction

from accounts.models import Account, Commodity
from transactions.models import Split, Transaction


class CsvImportService:
    @staticmethod
    def preview(file_content, delimiter=',', has_header=True, encoding='utf-8'):
        reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)
        rows = []
        header = None
        for i, row in enumerate(reader):
            if i == 0 and has_header:
                header = row
                continue
            rows.append(row)
            if len(rows) >= 10:
                break
        return {'header': header, 'rows': rows}

    @staticmethod
    def import_transactions(tenant, file_content, column_mapping, account_id, delimiter=',', has_header=True):
        account = Account.objects.get(id=account_id, tenant=tenant)
        reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)

        if has_header:
            next(reader)

        col_map = column_mapping
        imported = 0

        with transaction.atomic():
            for row in reader:
                if not row or all(not cell.strip() for cell in row):
                    continue

                try:
                    date_str = row[col_map['date']].strip()
                    description = row[col_map['description']].strip()
                    amount_str = row[col_map['amount']].strip().replace(',', '')
                    amount = Decimal(amount_str)
                except (IndexError, ValueError, KeyError):
                    continue

                tx = Transaction.objects.create(
                    tenant=tenant,
                    currency=account.commodity,
                    post_date=date_str,
                    description=description,
                    created_by=None,
                )

                Split.objects.create(
                    tenant=tenant, transaction=tx, account=account, value=-amount, quantity=-amount
                )
                imported += 1

        return imported


class CsvExportService:
    @staticmethod
    def export_transactions(tenant, account_id=None, start_date=None, end_date=None):
        splits = Split.objects.filter(tenant=tenant).select_related(
            'transaction', 'account'
        )

        if account_id:
            splits = splits.filter(account_id=account_id)
        if start_date:
            splits = splits.filter(transaction__post_date__gte=start_date)
        if end_date:
            splits = splits.filter(transaction__post_date__lte=end_date)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Description', 'Account', 'Value', 'Memo', 'Reconciled'])

        for split in splits:
            writer.writerow([
                split.transaction.post_date,
                split.transaction.description,
                split.account.full_name,
                split.value,
                split.memo,
                split.reconcile_state,
            ])

        return output.getvalue()
