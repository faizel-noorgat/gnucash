# GnuCash Reimagined

Modern multi-tenant cloud accounting SaaS platform, reimagined from GnuCash.

## Architecture

This is a **modular monolith** Django application with 5 bounded contexts:

1. **Identity & Access** (`apps.identity`) - User, Tenant, LegalEntity, Membership, RBAC
2. **Accounting Engine** (`apps.accounting`) - Core ledger, journals, multi-currency, banking
3. **Business Documents** (`apps.business_documents`) - Invoices, bills, parties, workflows
4. **Document Intelligence** (`apps.document_intelligence`) - OCR, extraction, matching
5. **Reporting & Analytics** (`apps.reporting`) - Financial reports, AI analytics

All bounded contexts share:
- Single PostgreSQL database with Row Level Security (RLS)
- Single Redis/Celery configuration
- Single REST API surface
- Unified authentication and multi-tenancy

## Key Features

- **Multi-tenant SaaS** with PostgreSQL RLS for data isolation
- **Accounting Practice support** for firms managing multiple clients
- **Multi-currency** with dual-field amount/value model
- **Double-entry bookkeeping** with strict immutability after posting
- **Document Intelligence** with OCR and learned accounting mappings
- **AI-assisted analytics** with deterministic accounting foundation

## Technology Stack

- **Backend:** Django 5.x, Django REST Framework
- **Database:** PostgreSQL 16+ with RLS
- **Task Queue:** Celery with Redis
- **Storage:** S3-compatible object storage
- **Testing:** pytest with golden accounting tests

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd gnucash-reimagined

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env with your database credentials

# Run migrations. Note the alias: migrations need the owning role and cannot
# run on `default`, which is the RLS-bound runtime role.
# See "Runtime and deploy database roles" below.
python manage.py migrate --database=deploy

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Docker Setup

```bash
# Start all services (PostgreSQL, Redis, Django, Celery)
docker compose up -d

# View logs
docker compose logs -f web

# Run migrations (the owning role; see "Runtime and deploy database roles")
docker compose exec web python manage.py migrate --database=deploy
```

## Runtime and deploy database roles

The application connects to PostgreSQL twice, with two different credentials
against the same database. Which one a connection uses decides whether tenant
isolation is enforced or merely declared.

| Alias | Role | Used by | Bound by RLS |
|---|---|---|---|
| `default` | `app_user` | every web and Celery query | yes |
| `deploy` | the owning role | `manage.py migrate --database=deploy` | no, and it cannot be |

A superuser - and a role with `BYPASSRLS` - sees through row-level security
even against a table carrying `FORCE ROW LEVEL SECURITY`. A runtime connection
naming either leaves the policies correct, reviewed, thoroughly tested and
enforcing nothing. `manage.py check` reports that as `rls.W001`.

Migrations run as the owning role because they have to. `FORCE ROW LEVEL
SECURITY` binds the table owner as well as everyone else, and the tenant
backfills in `apps/*/migrations` set a child's `tenant_id` from its parent with
no tenant context at all. A role the policies apply to would not fail on those
statements - it would update zero rows, in silence.

`app_user` is created by `common/rls/migrations/0001` with `NOLOGIN`, because a
provisioning migration must never invent a credential. Grant it one out of
band. The role does not exist until the first migration, and that migration
re-asserts only the four attributes that make the role safe to connect as -
`NOSUPERUSER`, `NOBYPASSRLS`, `NOCREATEDB`, `NOCREATEROLE` - never `LOGIN`,
which is the deployment's to grant and then stays granted. (Roles are
cluster-scoped while databases are not, so a `NOLOGIN` in that statement would
have revoked the credential cluster-wide every time a fresh database was
migrated, which is every `pytest` run.)

### A fresh development database

```bash
createdb gnucash_dev

# 1. Migrate first, as the owning role. This is also what creates app_user.
python manage.py migrate --database=deploy

# 2. Grant the runtime role a credential. The role does not exist before step 1,
#    and later migrations do not undo this.
psql -d gnucash_dev -c "ALTER ROLE app_user LOGIN PASSWORD 'app_user'"

# 3. Confirm the runtime connection is actually bound by the policies.
python manage.py check          # must print no rls.W001
```

Development reads `DB_USER`, `DB_PASSWORD`, `DB_OWNER_USER` and
`DB_OWNER_PASSWORD` (defaults: `app_user` and `postgres`); production takes
`DATABASE_URL` for the runtime role and `DEPLOY_DATABASE_URL` for the owning
one. `config/settings/test.py` is the one environment that cannot split the two
- the test runner migrates through the connection the tests then run as - so it
stays on a single privileged alias and the RLS suite assumes `app_user`
per test with `SET LOCAL ROLE`.

## Testing

```bash
# Run all tests
pytest

# Run golden accounting tests (highest priority)
pytest tests/golden/ -v

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/acceptance/
```

**Note:** Golden accounting tests require PostgreSQL (not SQLite) to validate RLS and database constraints.

## Project Structure

```
gnucash-reimagined/
├── config/              # Django project configuration
│   ├── settings/        # Environment-specific settings
│   ├── urls.py          # Root URL configuration
│   ├── celery.py        # Celery configuration
│   └── wsgi.py          # WSGI application
├── apps/                # Bounded contexts
│   ├── identity/        # Identity & Access
│   ├── accounting/      # Accounting Engine
│   ├── business_documents/  # Business Documents
│   ├── document_intelligence/  # Document Intelligence
│   └── reporting/       # Reporting & Analytics
├── common/              # Shared infrastructure
│   ├── rls/             # RLS models and utilities
│   └── middleware/      # Tenant context middleware
├── tests/               # Test suites
│   ├── golden/          # Golden accounting tests (critical)
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── acceptance/      # Acceptance tests
├── manage.py            # Django management script
├── pyproject.toml       # Project dependencies
├── Dockerfile           # Docker configuration
└── compose.yml          # Docker Compose configuration
```

## Key Architectural Decisions

- **ADR-001:** Modular Monolith for v1
- **ADR-002:** REST API Only for v1
- **ADR-003:** Banking/Reconciliation Merged into Accounting Engine
- **ADR-004:** Minimal Intercompany in v1
- **ADR-005:** Accounting Practice Access Model
- **ADR-006:** Document Provenance Audit Trail
- **ADR-007:** Simplified Infrastructure for Launch
- **ADR-008:** Multi-Tenancy with Shared-Schema PostgreSQL RLS
- **ADR-009:** Multi-Currency with Dual-Field Amount/Value Model
- **ADR-010:** Semantic Verification with Explicit State Machines

See `analysis/gnucash/REIMAGINED_ARCHITECTURE.md` for full details.

## Development

### Code Quality

```bash
# Run linting
ruff check apps/

# Format code
black apps/
isort apps/

# Type checking
mypy apps/
```

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Run migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

## License

[License information]

## Contributing

[Contributing guidelines]
