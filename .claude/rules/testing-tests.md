---
glob: "{backend,frontend,admin}/**/{test_*,*_test,test/**/*,tests/**/*}.{py,ts,tsx}"
---

# Testing Rules

## Backend Tests (pytest)
- Every public function, model method, API endpoint, and Celery task must have at least one test
- Unit tests for models and services — no HTTP calls, no database I/O in unit tests (use `pytest-django` `@pytest.mark.django_db` for DB tests)
- Integration tests for API endpoints — use DRF `APIClient` to test the full request/response cycle
- Property-based tests for double-entry invariants: every transaction's splits must sum to zero
- Security tests: tenant isolation (user A cannot access user B's data), auth bypass attempts on every endpoint
- Fixtures defined in `conftest.py` — not in individual test files
- Test data factories use `pytest-factoryboy` or `model_bakery` — no hardcoded test data

## Frontend Tests
- Unit tests for components using `@testing-library/react` — test user-visible behavior, not implementation details
- Unit tests for custom hooks using `renderHook` from `@testing-library/react`
- Integration tests for multi-component workflows (e.g., create transaction flow)
- E2E tests using Playwright — critical user journeys: login, create account, create transaction, view report
- No real API calls in unit tests — mock via MSW (Mock Service Worker) for frontend tests

## Test Naming
- Test functions named `test_<behaviour>_<expected_outcome>` — e.g., `test_split_sum_must_be_zero_raises_error`
- Test class names (pytest) follow `Test<Module>`, e.g., `TestTransactionModel`
- E2E test files named `e2e/<user-journey>.spec.ts` — one file per journey

## What Not to Test
- Do not test framework behavior (Django ORM correctness, DRF serializer basics)
- Do not test implementation details (private methods, internal state)
- Do not test shadcn/ui component internals — test that your component uses them correctly

## Coverage
- Minimum 80% line coverage for backend code
- Minimum 70% line coverage for frontend code
- Critical invariants (double-entry balance, tenant isolation) must have 100% coverage

## Sources
# Principles: [SRP (one test = one behaviour), Separation of Concerns (unit tests never cross layer boundaries)]
# Web: https://docs.pytest.org/en/stable/
# Web: https://testing-library.com/docs/react-testing-library/intro/
# Web: https://playwright.dev/docs/intro
# Date: 2026-04-16