---
glob: "backend/*/**/*.py"
---

# Backend — Python Language Rules

## Type Annotations
- Use type hints on all function signatures and class methods
- Use `from __future__ import annotations` at the top of all Python files
- Prefer `str | None` over `Optional[str]` syntax
- Type annotate Django model methods and properties that return computed values

## Module Structure
- One logical responsibility per module file
- Imports grouped: stdlib → third-party → local, separated by blank lines
- Use absolute imports within Django apps (`from accounts.models import Account`)
- Do not use wildcard imports (`from x import *`)

## Exception Handling
- Define custom exception classes in each Django app's `exceptions.py` for domain-specific errors
- Never catch `Exception` or `BaseException` — catch specific exception types
- Do not use bare `except:` clauses
- Log exceptions with context (tenant ID, user ID, action) at the point of handling

## String & Text
- Use f-strings for all string interpolation
- Use triple double-quotes (`"""`) for docstrings
- Docstrings required on all public functions and classes

## Async
- Use sync Django ORM calls — do not use `sync_to_async` wrappers outside of async contexts
- Celery tasks must be sync functions — Celery does not support async task functions

## Testing Conventions
- Test files named `test_<module>.py` in each app's `tests/` directory
- Use `pytest` as the test runner, not Django's default `manage.py test`
- Fixtures live in `tests/conftest.py` at the project level and `conftest.py` at the app level

## Sources
# Principles: [High Cohesion, Single Responsibility, Explicit over Implicit]
# Web: https://docs.djangoproject.com/en/stable/
# Web: https://docs.pytest.org/en/stable/
# Date: 2026-04-16