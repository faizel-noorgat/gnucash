# Document Intelligence Service

Bounded context for receipt/invoice OCR, structured extraction, matching, and
AI-assisted bookkeeping suggestions with a full, append-only audit trail of
every processing step.

## Responsibilities

- Accept documents uploaded via drag-drop, email, or API
- Persist documents in S3-compatible object storage with SHA-256 content hash
- Invoke OCR + extraction providers (AWS Textract, Google Document AI, ...)
- Recognize suppliers/customers via historical matching
- Detect duplicate invoices (invoice-number + supplier + amount + date)
- Match documents to bank transactions
- Maintain **explicit** organizational accounting mappings (never LLM memory)
- Produce AI-suggested accounting treatments with confidence scoring
- Route low-confidence work to a human review queue
- Preserve complete provenance: every extraction attempt is append-only

## Technology Stack

- **Framework:** Django 5.x
- **API:** Django REST Framework
- **Database:** PostgreSQL 16+ with Row Level Security
- **Background Jobs:** Celery + Redis (priority queues: `ocr_critical`, `normal`, `low`)
- **Object Storage:** S3-compatible (AWS S3, MinIO)
- **OCR:** AWS Textract (v1 default) with pluggable provider interface
- **LLM:** OpenAI / Anthropic (behind a provider interface)
- **Testing:** pytest + pytest-django + moto (S3 mocks)

## Domain Model

### Core Entities

- **Document**: uploaded file, stored in object storage, tenant-scoped
- **DocumentExtraction**: append-only log of every OCR/AI attempt (versioned)
- **DocumentMatch**: link to Party, AccountingDocument, or BankTransaction
- **AccountingMapping**: explicit organizational knowledge (supplier + line
  description → account / tax / dimension)
- **MappingSuggestion**: AI-generated suggestion with confidence score
- **ReviewQueue**: documents awaiting human review

### Audit Trail Requirements (per ADR-006, Architecture §5.3)

Every document persists:
- Original object-storage reference (immutable S3 key)
- Content hash (SHA-256, immutable)
- Upload timestamp + uploader
- OCR provider / model / version
- Extraction model / version + structured JSON result
- Accounting mapping used (if any)
- AI suggestion + confidence score + evidence
- Human correction (if any)
- Reviewer / approver
- Final resulting accounting document / journal entry

## API Endpoints

### Documents
- `POST   /api/documents/upload/`           - Upload document (multipart)
- `GET    /api/documents/`                   - List tenant documents
- `GET    /api/documents/{id}/`              - Retrieve document + provenance
- `GET    /api/documents/{id}/extractions/`  - List extraction attempts
- `GET    /api/documents/{id}/download/`     - Download original

### Extraction
- `POST   /api/documents/{id}/extract/`      - Trigger OCR/extraction
- `GET    /api/extractions/{id}/`            - Retrieval with full evidence

### Matching
- `POST   /api/documents/{id}/match/`        - Trigger matching pipeline
- `GET    /api/documents/{id}/matches/`      - List matches
- `POST   /api/documents/{id}/matches/{m}/accept/` - Accept match
- `POST   /api/documents/{id}/matches/{m}/reject/` - Reject match

### Review
- `GET    /api/review/`                      - Review queue
- `POST   /api/review/{id}/approve/`         - Approve extraction
- `POST   /api/review/{id}/correct/`         - Submit correction (creates v+1)

### Mappings
- `GET    /api/mappings/`                    - List learned mappings
- `POST   /api/mappings/`                    - Create explicit mapping
- `PUT    /api/mappings/{id}/`               - Update mapping
- `DELETE /api/mappings/{id}/`               - Retire mapping

## Development

```bash
poetry install
python manage.py migrate
poetry run pytest
python manage.py runserver
```

## Behavior Contract Rules (P0)

This service implements the following behavior-contract rules. Acceptance
tests live in `tests/acceptance/` and are tagged with the rule ID.

| Rule ID     | Rule                                                                 | Status |
|-------------|----------------------------------------------------------------------|--------|
| **BR-DI-001** | Document content hash is immutable after upload                    | Pending |
| **BR-DI-002** | Original object-storage file is immutable after upload             | Pending |
| **BR-DI-003** | Each OCR/AI extraction attempt is append-only (new version)        | Pending |
| **BR-DI-004** | Human corrections create new extraction version (never modify old) | Pending |
| **BR-DI-005** | Duplicate detection: same invoice-number + supplier + amount       | Pending |
| **BR-DI-006** | AI suggestions below confidence threshold require human review     | Pending |
| **BR-DI-007** | Accounting mappings are explicit organizational knowledge          | Pending |
| **BR-DI-008** | Document provenance captures complete audit trail                  | Pending |
| **BR-DI-009** | OCR/AI outputs never silently replace original or prior extraction | Pending |
| **BR-DI-010** | Documents are tenant-scoped via RLS + ORM default filters          | Pending |

## Dependencies

- **Identity & Access**: tenant context, user auth, RBAC
- **Accounting Engine**: reads Accounts, TaxRules, BankTransactions; receives
  JournalEntries resulting from posted document workflows (written by
  business-documents, NOT by document-intelligence directly)
- **Business Documents**: AccountingDocuments are the downstream target of a
  successful extraction + match + approve flow

## Security

- Multi-tenant isolation via PostgreSQL Row Level Security + ORM default filters
- No credentials in test fixtures — env-var placeholders only
  (`${AWS_ACCESS_KEY_ID}`, `${DATABASE_URL}`, `${OCR_PROVIDER_API_KEY}`)
- SHA-256 content hash verified on every download
- Original file in object storage is immutable (S3 Object Lock, WORM)
