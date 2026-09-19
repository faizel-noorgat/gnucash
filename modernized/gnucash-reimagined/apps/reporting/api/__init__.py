"""
Reporting & Analytics API.

Owns the HTTP surface for the bounded context:

* ``/definitions/`` — standard & custom report definitions
* ``/instances/`` — generated report instances
* ``/analytics/`` — deterministic analytic queries + optional AI explanation
* ``/dashboards/`` — dashboard CRUD and widget rendering

See ``apps.reporting.services`` for the domain logic behind each endpoint.
"""

from .urls import urlpatterns

__all__ = ["urlpatterns"]
