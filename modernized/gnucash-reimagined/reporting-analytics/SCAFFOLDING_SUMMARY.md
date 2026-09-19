# Reporting & Analytics — Scaffolding Summary

**Service:** reporting-analytics  
**Bounded Context:** Reporting & Analytics (Context #5 of 5)  
**Stack:** Django 5.x + DRF + Celery + Redis + PostgreSQL (RLS)  
**Date:** 2026-09-19

---

## What Was Scaffolded

### 1. Project Structure

```
reporting-analytics/
├── pyproject.toml                 # Poetry config, dependencies, pytest config
├── README.md                      # Service documentation
├── .env.example                   # Environment variable template
├── .gitignore                     # Git ignore rules
├── manage.py                      # Django management script
├── conftest.py                    # Root pytest fixtures
├── reporting_analytics/           # Django app
│   ├── __init__.py
│   ├── apps.py                    # Django AppConfig
│   ├── exceptions.py              # Domain exceptions + DRF handler
│   ├── middleware.py              # TenantContextMiddleware (RLS integration)
│   ├── urls.py                    # API routes
│   ├── tasks.py                   # Celery tasks
│   ├── settings/
│   │   ├── base.py                # Shared settings
│   │   ├── development.py         # Dev overrides
│   │   └── test.py                # Test settings (SQLite, eager Celery)
│   ├── models/
│   │   ├── reports.py             # ReportDefinition, ReportInstance
│   │   ├── dashboards.py          # Dashboard, DashboardWidget
│   │   └── analytics.py           # AnalyticQuery, AnalyticInsight
│   ├── serializers/
│   │   ├── reports.py             # DRF serializers for reports
│   │   ├── dashboards.py          # DRF serializers for dashboards
│   │   └── analytics.py           # DRF serializers for analytics
│   ├── views/
│   │   ├── reports.py             # Report API endpoints
│   │   ├── dashboards.py          # Dashboard API endpoints
│   │   └── analytics.py           # Analytics API endpoints
│   ├── services/
│   │   ├── report_generator.py    # Deterministic report generation
│   │   ├── analytics_engine.py    # Deterministic analytics (metrics + evidence)
│   │   ├── ai_explainer.py        # LLM-backed natural-language explanations
│   │   ├── kpis.py                # Pre-built KPI functions
│   │   └── golden_dependency.py   # Gate: accounting-engine golden tests
│   └── migrations/
│       └── __init__.py
└── tests/
    ├── __init__.py
    ├── conftest.py                # Test fixtures
    ├── test_acceptance.py         # Behavior-contract acceptance tests
    └── test_report_generator.py   # Unit tests for report generator
```

---

## Domain Model

### Reports

- **ReportDefinition** — Template for a standard or custom report (balance sheet, income statement, trial balance, etc.). Defines the parameter schema and query template.
- **ReportInstance** — A concrete, generated report. Lifecycle: `pending → running → succeeded | failed`. Stores the parameters, executed SQL, and result rows.

### Dashboards

- **Dashboard** — User-configurable container of widgets.
- **DashboardWidget** — Renders a single metric or chart using a report definition or pre-built KPI.

### Analytics

- **AnalyticQuery** — Deterministic query that produces metrics + evidence (variance analysis, trend detection, anomaly surfacing, etc.).
- **AnalyticInsight** — AI-generated insight backed by concrete evidence. **Mandatory:** every insight must reference at least one ledger object (journal entry, account, document). Insights without evidence are rejected at the model layer to prevent hallucinations.

---

## Key Design Principles

1. **Ledger is the source of truth.** Reporting reads from the Accounting Engine; it never writes financial facts.
2. **Determinism first.** A report generated twice with the same inputs produces identical output.
3. **Explainable AI.** Every AI-generated insight carries a list of evidence references (account, journal entry, journal line, document).
4. **Tenant isolation.** Every query is scoped to a single tenant via the shared-schema RLS session variable; no cross-tenant leakage.
5. **Async for heavy work.** Large reports and AI queries are executed as Celery tasks; the API returns a `ReportInstance` in `pending` state and the client polls until `succeeded`.

---

## Behavior-Contract Rules

The AI_NATIVE_SPEC does not define explicit `BR-RPT-xxx` rules for the reporting context (unlike `BR-ACCT-xxx` for the accounting engine). The following rules are derived from the architectural requirements in Section 6 and Section 9.7:

| Rule ID | Description | Test |
|---------|-------------|------|
| **RPT-001** | Reports are deterministic — same input → same output. | `test_report_is_deterministic` |
| **RPT-002** | Reports are tenant-scoped — no cross-tenant leakage. | `test_report_is_tenant_scoped` |
| **RPT-003** | AI insights require evidence — no hallucinated insights. | `test_insight_requires_evidence`, `test_explainer_refuses_no_evidence` |
| **RPT-004** | Report lifecycle state transitions are explicit. | `test_report_lifecycle_transitions`, `test_report_can_be_cancelled_from_pending`, `test_report_cannot_be_cancelled_from_succeeded` |
| **RPT-005** | Report parameters are validated before generation. | `test_report_parameters_validation` |
| **RPT-006** | AI explainer is never asked to perform arithmetic. | `test_explainer_prompt_does_not_ask_for_arithmetic` |
| **RPT-007** | Golden accounting tests must pass before reporting on posted data. | `test_golden_dependency_gate` |

All acceptance tests are tagged with `@pytest.mark.acceptance` and `@pytest.mark.rule("<rule-id>")`.

---

## Dependency on Accounting Engine

This service is a *consumer* of the Accounting Engine's ledger. The Accounting Engine's **golden accounting tests** (double-entry balancing, multi-currency semantics, trading-account balancing, reconciliation, reversal/correcting entries) must pass before any reporting result that depends on posting can be considered correct.

The `services/golden_dependency.py` module encodes this contract: a reporting-analytics acceptance test marked with `@pytest.mark.golden_dependency` will be skipped unless the accounting-engine golden suite reports green via a well-known manifest file (`accounting-engine/manifests/golden.lock`).

---

## API Endpoints

### Reports

- `GET /api/report-definitions/` — List report definitions
- `GET /api/report-definitions/{guid}/` — Retrieve a report definition
- `POST /api/report-instances/` — Create a new report instance (enqueues Celery task)
- `GET /api/report-instances/` — List report instances
- `GET /api/report-instances/{guid}/` — Retrieve a report instance
- `POST /api/report-instances/{guid}/cancel/` — Cancel a pending/running report
- `GET /api/report-instances/{guid}/result/` — Get the result rows of a succeeded report

### Dashboards

- `GET /api/dashboards/` — List dashboards
- `POST /api/dashboards/` — Create a dashboard
- `GET /api/dashboards/{guid}/` — Retrieve a dashboard
- `PUT /api/dashboards/{guid}/` — Update a dashboard
- `DELETE /api/dashboards/{guid}/` — Delete a dashboard

### Analytics

- `GET /api/analytic-queries/` — List analytic queries
- `POST /api/analytic-queries/` — Create a new analytic query (enqueues Celery task)
- `GET /api/analytic-queries/{guid}/` — Retrieve an analytic query
- `GET /api/analytic-insights/` — List analytic insights
- `GET /api/analytic-insights/{guid}/` — Retrieve an analytic insight
- `POST /api/analytic-insights/{guid}/review/` — Mark an insight as reviewed or rejected

---

## Technology Choices

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Backend Framework | Django 5.x | Mature, batteries-included, strong ORM, excellent admin |
| API | Django REST Framework | REST only for v1; GraphQL deferred to v2 |
| Database | PostgreSQL 16+ | Robust, JSONB for flexible fields, excellent for multi-tenant RLS |
| Multi-Tenancy | Shared-schema PostgreSQL with RLS | Database-enforced isolation (ADR-008) |
| Background Jobs | Celery + Redis broker | Mature, reliable, supports task routing, retries, monitoring |
| Caching | Redis | Fast, session storage, Celery broker |
| AI / LLM | Pluggable (stub, OpenAI, Anthropic) | Provider-agnostic; selected via `LLM_PROVIDER` env var |
| Analytics | numpy, pandas | Deterministic metrics computation |

---

## Running the Tests

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run acceptance tests only
poetry run pytest -m acceptance

# Run unit tests only
poetry run pytest -m "not acceptance"
```

---

## Environment Variables

See `.env.example` for the full list. Key variables:

- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `LLM_PROVIDER` — One of: `stub`, `openai`, `anthropic`
- `LLM_API_KEY` — API key for the LLM provider (if not `stub`)
- `ACCOUNTING_ENGINE_URL` — URL of the Accounting Engine service
- `ACCOUNTING_ENGINE_GOLDEN_MANIFEST` — Path to the golden-tests manifest

---

## Next Steps

1. **Migrations** — Run `python manage.py makemigrations` and `python manage.py migrate` to create the database schema.
2. **Integration with Accounting Engine** — Implement the actual SQL queries in `report_generator.py` to read from the Accounting Engine's ledger tables.
3. **RLS Policies** — Define PostgreSQL RLS policies on the Accounting Engine tables to enforce tenant isolation at the database layer.
4. **Golden Tests** — Ensure the Accounting Engine's golden accounting tests pass before running the reporting acceptance suite.
5. **LLM Provider** — Implement the OpenAI and Anthropic providers in `ai_explainer.py` (currently stubbed).
6. **Dashboard Widgets** — Implement the actual KPI functions in `kpis.py` to query the Accounting Engine.

---

## Notes

- **No credential literals** are committed to source control. All secrets come from the environment.
- **Tenant isolation** is enforced at three layers: ORM filters, RLS session variables, and database policies (defense-in-depth).
- **AI insights** are rejected if they lack evidence — this prevents hallucinated insights from being shown to users.
- **Report generation** is async for large datasets; the API returns a `ReportInstance` in `pending` state and the client polls until `succeeded`.
- **The golden dependency gate** ensures that reporting tests that touch posted data are only run after the Accounting Engine's golden tests pass.
