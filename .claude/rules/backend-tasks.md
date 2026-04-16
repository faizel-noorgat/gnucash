---
glob: "backend/*/tasks.py"
---

# Backend — Celery Task Rules

## Task Definition
- All Celery tasks must be defined in `tasks.py` within each Django app
- Use `@shared_task` decorator — do not use `@app.task` to avoid circular imports
- Every task function must have a descriptive `name` argument in `@shared_task(name="app_name.task_name")`

## Task Design
- Tasks must be idempotent — retrying a task must not produce duplicate side effects
- Tasks must not accept Django model instances as arguments — pass primary key IDs only
- Tasks must re-fetch model instances from the database at the start of execution
- Long-running tasks must use `self.retry()` with exponential backoff on transient failures

## Error Handling
- Set `max_retries` and `default_retry_delay` on tasks that call external services (OCR, Stripe, price APIs)
- Log errors with task name, parameters (excluding secrets), and exception details
- Do not catch and swallow exceptions — let Celery handle retries and dead-letter queuing

## Task Categories
- **OCR processing** (`receipts.process_ocr`): retry on API failures, store intermediate results
- **Recurring transactions** (`recurring.run_scheduled_transactions`): use Celery beat schedule, skip already-run
- **Notification digests** (`notifications.send_digest`): batch per-user, use `atomic = False` for large batches
- **Report generation** (`reports.generate_pdf`): store result in Cloudflare R2, notify on completion
- **Audit log purge** (`audit.purge_old_logs`): batch delete, run monthly via Celery beat
- **Stripe sync** (`billing.sync_stripe_data`): idempotent, retry on network failures

## Celery Beat Schedule
- Define schedules in `backend/gnucash_web/celery.py` — not in app-level files
- Use `crontab` for fixed-time schedules, `timedelta` for interval-based schedules
- Recurring transaction execution uses Celery beat with a daily check — not per-transaction timers

## Sources
# Principles: [Idempotency, Fault Tolerance, Separation of Concerns (tasks are workers, not controllers)]
# Web: https://docs.celeryq.dev/en/stable/userguide/tasks.html
# Date: 2026-04-16