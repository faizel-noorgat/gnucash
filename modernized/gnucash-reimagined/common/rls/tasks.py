"""
Celery base task that establishes the same tenant context as an HTTP request.

A background task has no middleware and no request, so without this the RLS
policies would run with no ``app.current_tenant_id`` set and every query would
return zero rows - failing closed, but silently and confusingly. The context has
to be re-established inside the worker for the same reason it is established per
request: the session variable is transaction-local, so it never survives the
hand-off that queued the job.

The whole task body runs inside one ``transaction.atomic()``. That is not
decoration: ``SET LOCAL`` is discarded at the end of the transaction it was
issued in, so a context set outside a transaction is a no-op. The atomic block
is what makes the context outlive the statement that set it and cover every
query the task makes.
"""

from django.db import transaction

from celery import Task
from common.middleware.tenant import TenantContextManager


class TenantScopedTask(Task):
    """Base task for work that needs tenant context for RLS.

    Subclass it and pass the scope as keyword arguments::

        @shared_task(base=TenantScopedTask, bind=True)
        def rebuild_report(self, report_id, *, tenant_id, user_id=None, entity_id=None):
            ...

    ``tenant_id`` is required. A task that declares itself tenant-scoped and
    runs without one would read nothing and write nothing - the failures would
    look like missing data rather than a missing argument - so it raises
    instead. ``user_id`` and ``entity_id`` are optional and narrow the context
    further when present.
    """

    abstract = True

    #: Keyword arguments consumed to build the context. They are left in the
    #: task's own kwargs as well, so the body can still use them.
    tenant_kwarg = "tenant_id"
    user_kwarg = "user_id"
    entity_kwarg = "entity_id"

    def __call__(self, *args, **kwargs):
        tenant_id = kwargs.get(self.tenant_kwarg)
        if not tenant_id:
            raise ValueError(
                f"{type(self).__name__} is tenant-scoped but was called without "
                f"'{self.tenant_kwarg}'. Refusing to run without tenant context: "
                "RLS would silently return no rows for every query."
            )

        with transaction.atomic(), TenantContextManager(
            tenant_id,
            kwargs.get(self.user_kwarg),
            kwargs.get(self.entity_kwarg),
        ):
            return super().__call__(*args, **kwargs)
