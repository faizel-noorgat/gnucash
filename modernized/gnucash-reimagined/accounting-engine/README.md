# Accounting Engine - FVA Accounting Platform

Core accounting engine for the FVA Accounting Platform reimagined system.

## Overview

The Accounting Engine is the **core bounded context** of the FVA Accounting Platform. It implements:

- **Double-entry bookkeeping** with exact-zero balance enforcement
- **Multi-currency support** with dual-field amount/value model (ADR-009)
- **Hierarchical chart of accounts** with fundamental type detection
- **Journal posting** with immutability enforcement via PostgreSQL triggers (ADR-010)
- **Banking integration** and reconciliation (merged per ADR-003)
- **Minimal intercompany** functionality (per ADR-004)
- **Tax calculation** with versioned rules and discount ordering modes
- **Immutable audit trail** for all financial actions

## Technology Stack

- **Framework:** Django 5.x
- **API:** Django REST Framework
- **Database:** PostgreSQL 16+ with Row Level Security (RLS)
- **Background Jobs:** Celery + Redis
- **Testing:** pytest + factory-boy

## Architecture Decisions

- **ADR-009:** Multi-currency dual-field amount/value model with hidden trading accounts
- **ADR-010:** Database-level immutability via PostgreSQL BEFORE UPDATE/DELETE triggers
- **ADR-003:** Banking/reconciliation merged into Accounting Engine
- **ADR-004:** Minimal intercompany functionality in v1

## Behavior Contract Rules

This service implements the following P0 behavior-contract rules:

### Transaction Balance Invariants
- **BR-ACCT-001:** Transaction balance invariant (double-entry)
- **BR-ACCT-002:** Multi-currency transaction balance per commodity
- **BR-ACCT-003:** Transaction edit atomicity

### Account Type Invariants
- **BR-ACCT-006:** Account fundamental types (ASSET/LIABILITY/INCOME/EXPENSE/EQUITY)
- **BR-ACCT-007:** AP/AR type detection
- **BR-ACCT-010:** Root account cannot have parent

### Reconciliation Invariants
- **BR-SPLIT-001:** Split reconciliation states (n/c/y/f/v)
- **BR-SPLIT-004:** Reconciled balance only includes reconciled splits

### Tax Calculation Invariants
- **BR-TAX-001:** Tax table entry types (VALUE/PERCENT)
- **BR-TAX-002:** Tax-included price back-computation
- **BR-TAX-003:** Discount ordering modes (PRETAX/SAMETIME/POSTTAX)

### Foreign Exchange Invariants
- **BR-FX-001:** Price lookup nearest-in-time

### Lot Invariants
- **BR-LOT-001:** Lot closure criterion (balance = exactly zero)
- **BR-LOT-002:** Lot balance cached closure flag

## Domain Model

### Core Entities

- **Commodity/Currency:** Tradable items (currencies, securities)
- **ExchangeRate:** Historical exchange rates with daily granularity
- **Account:** Hierarchical chart of accounts with fundamental types
- **JournalEntry:** Double-entry transactions (draft → posted → immutable)
- **JournalLine:** Individual debits/credits with dual-field amount/value
- **FiscalPeriod:** Period-end controls (open/closed/locked)
- **TaxRule:** Versioned tax rules with effective dates
- **PaymentTerm:** Versioned payment terms
- **BankAccount/BankStatement/BankTransaction:** Banking integration
- **BankReconciliation:** Bank reconciliation sessions
- **IntercompanyRelationship:** Links between legal entities
- **InterEntityEvent:** Coordination object for intercompany transactions
- **Lot:** Groups splits for inventory/stock tracking
- **AuditEvent:** Immutable audit trail

### Multi-Currency Semantics (ADR-009)

The system uses a dual-field amount/value model:

- **JournalLine.amount:** Quantity in the account's commodity (e.g., USD 10,000)
- **JournalLine.value:** Quantity in the transaction's balancing currency (e.g., SGD 13,400)
- **JournalEntry.transaction_currency:** Explicit currency for the journal

Trading accounts are used internally for multi-currency balancing but hidden from users.

### Immutability Enforcement (ADR-010)

Posted journal entries are immutable at the database level:

- PostgreSQL BEFORE UPDATE / BEFORE DELETE triggers prevent modification
- Application-layer guards provide defense-in-depth
- Separate ImmutablePostedJournalEntry/JournalLine models represent frozen data
- Formal reversal/correcting entry workflow for changes

## API Endpoints

### Commodities & Currencies
- `GET/POST /api/v1/commodities/` - List/create commodities
- `GET/PUT/DELETE /api/v1/commodities/{guid}/` - Retrieve/update/delete commodity
- `GET/POST /api/v1/exchange-rates/` - List/create exchange rates

### Chart of Accounts
- `GET/POST /api/v1/accounts/` - List/create accounts
- `GET/PUT/DELETE /api/v1/accounts/{guid}/` - Retrieve/update/delete account
- `GET /api/v1/accounts/{guid}/balance/` - Get account balance
- `GET /api/v1/accounts/{guid}/reconciled_balance/` - Get reconciled balance

### Journal Entries
- `GET/POST /api/v1/journal-entries/` - List/create journal entries
- `GET/PUT/DELETE /api/v1/journal-entries/{guid}/` - Retrieve/update/delete entry
- `POST /api/v1/journal-entries/{guid}/post_entry/` - Post entry (make immutable)
- `POST /api/v1/journal-entries/{guid}/reverse/` - Create reversal entry
- `POST /api/v1/journal-entries/{guid}/correct/` - Create correcting entry

### Fiscal Periods
- `GET/POST /api/v1/fiscal-periods/` - List/create fiscal periods
- `POST /api/v1/fiscal-periods/{guid}/close/` - Close period
- `POST /api/v1/fiscal-periods/{guid}/lock/` - Lock period (permanent)

### Tax & Payment Terms
- `GET/POST /api/v1/tax-rules/` - List/create tax rules
- `GET/POST /api/v1/payment-terms/` - List/create payment terms

### Banking
- `GET/POST /api/v1/bank-accounts/` - List/create bank accounts
- `GET/POST /api/v1/bank-transactions/` - List bank transactions
- `GET/POST /api/v1/bank-reconciliations/` - List/create reconciliations

### Intercompany
- `GET/POST /api/v1/intercompany-relationships/` - List/create relationships
- `GET/POST /api/v1/intercompany-events/` - List/create events
- `POST /api/v1/intercompany-events/{guid}/accept/` - Accept event
- `POST /api/v1/intercompany-events/{guid}/reject/` - Reject event

### Audit
- `GET /api/v1/audit-events/` - List audit events (read-only)

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set environment variables
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
python manage.py migrate

# Apply PostgreSQL triggers
psql -d accounting_engine -f triggers/immutability_triggers.sql

# Create superuser
python manage.py createsuperuser
```

### Running Tests

```bash
# Run all tests
pytest

# Run acceptance tests only
pytest -m acceptance

# Run golden accounting tests
pytest -m golden

# Run with coverage
pytest --cov=accounting_engine --cov-report=html
```

### Development Server

```bash
python manage.py runserver
```

## Security Invariants

- No credential literals from legacy code
- All secrets read from environment variables
- Database isolation via PostgreSQL RLS
- Immutable audit trail
- Posted journal immutability enforced at database level

## Configuration

See `.env.example` for all configuration options.

Key settings:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `DJANGO_SECRET_KEY` - Django secret key
- `CELERY_BROKER_URL` - Celery broker URL

## License

Proprietary - FVA Accounting Platform
