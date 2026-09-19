# Reporting & Analytics

Bounded context responsible for financial reports, AI-assisted analytics,
and dashboards in the FVA Accounting Platform.

## Responsibilities

- **Deterministic financial reports** — Balance Sheet, Income Statement,
  Cash Flow Statement, Trial Balance, General Ledger, Aged Receivables,
  Aged Payables. Implemented as pure SQL queries against the Accounting
  Engine's ledger; no approximation, no caching of financial facts.
- **AI-assisted analytics (P1)** — Variance analysis, trend detection,
  anomaly surfacing, natural-language explanations. Every AI conclusion is
  traceable to concrete ledger rows and deterministic intermediate metrics.
  The LLM is used only for explanation, never for arithmetic.
- **Dashboards & KPIs** — User-configurable dashboards; server-rendered
  metric tiles sourced from the same deterministic report primitives.

## Design Principles

1. **Ledger is the source of truth.** Reporting reads from the Accounting
   Engine; it never writes financial facts.
2. **Determinism first.** A report generated twice with the same inputs
   produces identical output. Randomness is confined to non-financial
   presentation (e.g. colour palette on a chart).
3. **Explainable AI.** Every AI-generated insight carries a list of
   evidence references (account, journal entry, journal line, document).
4. **Tenant isolation.** Every query is scoped to a single tenant via
   the shared-schema RLS session variable; no cross-tenant leakage.
5. **Async for heavy work.** Large reports and AI queries are executed
   as Celery tasks; the API returns a `ReportInstance` in `pending`
   state and the client polls until `succeeded`.

## Dependency on Accounting Engine

This service is a *consumer* of the Accounting Engine's ledger. The
Accounting Engine's **golden accounting tests** (double-entry balancing,
multi-currency semantics, trading-account balancing, reconciliation,
reversal/correcting entries) must pass before any reporting result that
depends on posting can be considered correct.

The `tests/golden_dependency_gate.py` module encodes this contract: a
reporting-analytics acceptance test marked with `@pytest.mark.golden_dependency`
will be skipped unless the accounting-engine golden suite reports green
via a well-known manifest file (`accounting-engine/manifests/golden.lock`).

## Running

```bash
poetry install
poetry run pytest                    # unit + integration
poetry run pytest -m acceptance      # behavior-contract tests only
```

## Environment

See `.env.example` for required configuration. No secret literal is ever
committed; all credentials come from the environment.
