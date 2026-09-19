"""
RLS infrastructure package.

This package is an installed Django app (see ``apps.py``), so Django imports it
while it is still populating the app registry. Re-exporting the abstract models
here - as this module used to - therefore runs ``models.Model`` subclass
construction before the registry is ready, and the whole process dies with
``AppRegistryNotReady: Apps aren't loaded yet``.

Import the mixins from their real home instead::

    from common.rls.models import EntityScopedModel, TenantScopedModel

Nothing outside this package imported them, so removing the re-export broke no
callers.
"""
