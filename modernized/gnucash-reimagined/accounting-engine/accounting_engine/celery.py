"""Celery configuration for accounting-engine project."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accounting_engine.settings")

app = Celery("accounting_engine")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f"Request: {self.request!r}")
