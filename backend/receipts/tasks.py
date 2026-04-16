from __future__ import annotations

from celery import shared_task


@shared_task(name='receipts.process_ocr')
def process_ocr(receipt_id):
    pass


@shared_task(name='receipts.learn_from_correction')
def learn_from_correction(receipt_id, category_id):
    pass
