"""Celery application configuration for Document Intelligence."""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "document_intelligence.settings.base")

app = Celery("document_intelligence")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["document_intelligence"])

# Priority queues
app.conf.task_queues = {
    "ocr_critical": {
        "exchange": "ocr_critical",
        "routing_key": "ocr_critical",
    },
    "normal": {
        "exchange": "normal",
        "routing_key": "normal",
    },
    "low": {
        "exchange": "low",
        "routing_key": "low",
    },
}

app.conf.task_default_queue = "normal"
