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

# Run migrations
python manage.py migrate

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

# Run migrations
docker compose exec web python manage.py migrate
```

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
