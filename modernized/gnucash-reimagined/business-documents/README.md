# Business Documents Service

Bounded context for managing parties (customers, vendors, employees), accounting documents
(invoices, bills, credit notes), and approval workflows.

## Responsibilities

- Party management with role-based polymorphism
- Accounting document lifecycle (draft → approved → posted)
- Document line items with tax and discount calculations
- Approval workflows
- Integration with Accounting Engine for posting
- Attachment management via object storage

## Technology Stack

- **Framework:** Django 5.x
- **API:** Django REST Framework
- **Database:** PostgreSQL 16+ with Row Level Security
- **Background Jobs:** Celery + Redis
- **Object Storage:** S3-compatible (AWS S3, MinIO)
- **Testing:** pytest + pytest-django

## Domain Model

### Core Entities

- **Party**: Unified entity for customers, vendors, employees, connected entities
- **AccountingDocument**: Unified entity for invoices, bills, credit notes with direction
- **DocumentLine**: Line items with quantity, unit price, tax, account mapping
- **ApprovalWorkflow**: Configurable approval chains
- **ApprovalStep**: Individual approval with approver and status

### Key Behaviors

- Draft documents may be incomplete/unbalanced
- Posting creates JournalEntry in Accounting Engine
- Posted documents cannot be modified (only corrected via reversal/credit note)
- Attachments stored in object storage, linked to document

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
- `POST /api/documents/{id}/post/` - Post document (one-way)
- `POST /api/documents/{id}/approve/` - Approve document

### Document Lines
- `GET /api/documents/{doc_id}/lines/` - List lines
- `POST /api/documents/{doc_id}/lines/` - Create line
- `PUT /api/documents/{doc_id}/lines/{id}/` - Update line
- `DELETE /api/documents/{doc_id}/lines/{id}/` - Delete line

### Attachments
- `GET /api/documents/{doc_id}/attachments/` - List attachments
- `POST /api/documents/{doc_id}/attachments/` - Upload attachment
- `GET /api/attachments/{id}/` - Download attachment

## Development

```bash
# Install dependencies
poetry install

# Run migrations
python manage.py migrate

# Run tests
poetry run pytest

# Run server
python manage.py runserver
```

## Behavior Contract Rules

This service implements the following P0 business rules:

- **BR-BUS-001**: Invoice posting is one-way (once posted, cannot post again)
- **BR-BUS-002**: Invoice amounts are always stored positive (sign determined by owner type)

## Dependencies

- **Accounting Engine**: Receives JournalEntry creation on document posting
- **Identity & Access**: Provides tenant context, user authentication, authorization
- **Document Intelligence**: Receives OCR-extracted documents for matching

## Security

- Multi-tenant isolation via PostgreSQL Row Level Security
- Tenant context enforced at middleware and ORM layers
- Immutable posted documents (database-level enforcement)
- Audit trail for all financial actions
