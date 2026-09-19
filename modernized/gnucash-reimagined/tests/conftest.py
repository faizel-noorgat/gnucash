"""
Project-wide test configuration for GnuCash Reimagined.

Context-specific fixtures live in tests/<bounded_context>/conftest.py, so that a
fixture defined by one context can never shadow another's.

Shared fixture names currently in use across context conftests:
    tenant, legal_entity, user

NOTE: this file deliberately does NOT override pytest-django's `django_db_setup`.
An earlier version did, replacing it with a fixture that only mutated
settings.DATABASES and never created the database - which suppressed test
database creation entirely. Database configuration belongs in
config/settings/test.py, which already pins PostgreSQL.
"""
