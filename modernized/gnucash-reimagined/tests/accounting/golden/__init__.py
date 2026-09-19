"""
Golden accounting tests - highest priority verification suite.

These tests verify critical accounting invariants extracted from GnuCash.
They must be executed against PostgreSQL (not SQLite) to validate RLS and
database-level constraints.
"""
