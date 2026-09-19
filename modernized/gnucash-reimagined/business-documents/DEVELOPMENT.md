# Business Documents Service - Development Guide

## Quick Start

```bash
# 1. Install dependencies
poetry install

# 2. Set up environment variables
cp .env.example .env
# Edit .env with your settings

# 3. Set up database
createdb fva_dev
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser

# 5. Run development server
python manage.py runserver
```

## Project Structure

```
business-documents/
├── business_documents/          # Django app
│   ├── models/                  # Domain models
│   │   ├── party.py            # Party (customer/vendor/employee)
│   │   ├── document.py         # AccountingDocument (invoice/bill/credit note)
│   │   ├── line.py             # DocumentLine (line items)
│   │   ├── attachment.py       # DocumentAttachment
│   │   └── approval.py         # ApprovalWorkflow, ApprovalStep
│   ├── serializers/            # DRF serializers
│   ├── views/                  # DRF viewsets
│   ├── services/               # Business logic
│   │   ├── document_posting.py # Posting to accounting engine
│   │   └── storage.py          # S3 storage service
│   ├── tests/                  # Test suite
│   ├── middleware.py           # Tenant context middleware
│   ├── permissions.py          # Permission classes
│   └── urls.py                 # URL routing
├── migrations/                  # Database migrations
├── manage.py                    # Django management script
└── pyproject.toml              # Project dependencies
```

## Key Concepts

### Parties
Unified entity for customers, vendors, employees. A party can have multiple roles.

### Accounting Documents
Unified entity for invoices, bills, credit notes with:
- Direction: SALES or PURCHASE
- Type: INVOICE, BILL, CREDIT_NOTE, DEBIT_NOTE
- Status: DRAFT → PENDING_APPROVAL → APPROVED → POSTED

### Document Lines
Line items with:
- Quantity and unit price
- Account mapping
- Tax treatment
- Discount ordering modes (PRETAX, SAMETIME, POSTTAX)

### Approval Workflows
Configurable approval chains with:
- Multiple steps
- Role-based or user-specific approvers
- Optional threshold amounts

## API Endpoints

### Parties
- `GET /api/parties/` - List parties
- `POST /api/parties/` - Create party
- `GET /api/parties/{id}/` - Retrieve party
- `PUT /api/parties/{id}/` - Update party
- `DELETE /api/parties/{id}/` - Delete party

### Accounting Documents
- `GET /api/documents/` - List documents
- `POST /api/documents/` - Create document
- `GET /api/documents/{id}/` - Retrieve document
- `PUT /api/documents/{id}/` - Update document
- `POST /api/documents/{id}/submit_for_approval/` - Submit for approval
- `POST /api/documents/{id}/approve/` - Approve document
- `POST /api/documents/{id}/post_document/` - Post to accounting engine
- `POST /api/documents/{id}/cancel/` - Cancel document

### Document Lines
- `GET /api/documents/{doc_id}/lines/` - List lines
- `POST /api/documents/{doc_id}/lines/` - Create line
- `PUT /api/documents/{doc_id}/lines/{id}/` - Update line
- `DELETE /api/documents/{doc_id}/lines/{id}/` - Delete line

### Attachments
- `GET /api/documents/{doc_id}/attachments/` - List attachments
- `POST /api/documents/{doc_id}/attachments/` - Upload attachment
- `GET /api/attachments/{id}/download/` - Download attachment

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=business_documents

# Run specific test file
poetry run pytest business_documents/tests/test_acceptance.py
```

## Behavior Contract Rules

This service implements:

- **BR-BUS-001**: Invoice posting is one-way
- **BR-BUS-002**: Invoice amounts are always stored positive
- **BR-TAX-003**: Discount ordering modes

## Dependencies

### Accounting Engine
- Receives JournalEntry creation on document posting
- Provides Account, Currency, TaxRule models

### Identity & Access
- Provides Tenant, LegalEntity, User models
- Provides authentication and authorization

### Document Intelligence
- Sends OCR-extracted documents for matching

## Security

- Multi-tenant isolation via PostgreSQL Row Level Security
- Tenant context enforced at middleware layer
- Immutable posted documents
- Audit trail for all actions

## Deployment

```bash
# Build for production
poetry build

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start with gunicorn
gunicorn business_documents.wsgi:application --bind 0.0.0.0:8000
```
