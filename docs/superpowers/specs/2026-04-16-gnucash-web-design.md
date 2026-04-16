# GnuCash Web - Design Specification

**Date:** 2026-04-16  
**Status:** Approved  
**Type:** Multi-tenant Personal Finance SaaS

---

## 1. Overview

GnuCash Web is a modern, multi-tenant web application that replicates GnuCash's full double-entry accounting capabilities for personal finance users. Built with Django, React, and PostgreSQL, it targets individual users and households who need powerful accounting with a modern UX.

### 1.1 Product Goals

- Faithful double-entry accounting with hierarchical accounts
- Modern, accessible UI with offline support
- Multi-tenant SaaS with per-user pricing
- Cloud OCR with ML-based auto-categorization
- Comprehensive financial reporting
- Investment tracking with lot management

### 1.2 Target Users

- Personal finance users (not business accounting)
- Households with shared finances (multi-user tenants)
- GnuCash migrants seeking modern UX
- Users in regions with limited bank sync coverage (South Africa, UAE, etc.)

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │  Tenant App     │  │   Admin Hub     │                       │
│  │  (React+Vite)   │  │   (React+Vite)  │                       │
│  └────────┬────────┘  └────────┬────────┘                       │
└───────────┼────────────────────┼────────────────────────────────┘
            │                    │
            │      HTTPS         │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Nginx (Reverse Proxy)                       │
│                           SSL Termination                        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │   Gunicorn    │ │   Gunicorn    │ │    Celery     │
    │  (Tenant API) │ │  (Admin API)  │ │    Worker     │
    └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
            │                 │                 │
            └─────────────────┼─────────────────┘
                              │
                              ▼
                  ┌─────────────────────┐
                  │   PostgreSQL 15+    │
                  │  (Single DB, RLS)   │
                  └──────────┬──────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │   Redis       │ │  Cloudflare   │ │   Backup      │
    │   (Cache/     │ │     R2        │ │   Storage     │
    │    Broker)    │ │  (Attachments)│ │               │
    └───────────────┘ └───────────────┘ └───────────────┘
```

### 2.2 Repository Structure

```
gnucash-web/
├── backend/                 # Django application
│   ├── accounts/           # Account models, views, serializers
│   ├── transactions/       # Transaction, split models
│   ├── budgets/            # Budget models, calculations
│   ├── reports/            # Report generation
│   ├── investments/        # Investment tracking
│   ├── receipts/           # OCR, ML categorization
│   ├── recurring/          # Scheduled transactions
│   ├── reconciliation/     # Account reconciliation
│   ├── notifications/      # Notification system
│   ├── audit/              # Audit logging
│   ├── billing/            # Stripe integration
│   ├── tenants/            # Multi-tenancy configuration
│   └── gnucash_web/        # Project settings, URLs
├── frontend/               # Tenant-facing React app
│   ├── src/
│   │   ├── components/     # shadcn/ui components
│   │   ├── features/       # Feature modules
│   │   ├── hooks/          # Custom hooks
│   │   ├── lib/            # Utilities, API client
│   │   └── stores/         # Zustand stores
│   └── public/
├── admin/                  # Admin hub React app
│   ├── src/
│   │   ├── components/
│   │   ├── features/
│   │   └── ...
│   └── public/
├── docker-compose.yml      # Local development
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

### 2.3 API Design

- **Style:** REST with Django REST Framework
- **Versioning:** URL path (`/api/v1/`)
- **Authentication:** JWT tokens + session cookies
- **Tenant scoping:** `X-Tenant-ID` header (validated against user's tenants)

---

## 3. Data Model

### 3.1 Core Models

#### Tenant
```
- id: UUID
- name: String
- slug: String (unique)
- created_at: DateTime
- trial_ends_at: DateTime
- stripe_customer_id: String
```

#### User
```
- id: UUID
- email: String (unique)
- password_hash: String (Argon2)
- is_active: Boolean
- created_at: DateTime
- last_login_at: DateTime
```

#### TenantMembership
```
- id: UUID
- tenant: ForeignKey(Tenant)
- user: ForeignKey(User)
- role: Enum [OWNER, ADMIN, MEMBER]
- joined_at: DateTime
```

#### Account
```
- id: UUID
- tenant: ForeignKey(Tenant)
- parent: ForeignKey(Account, nullable)
- name: String
- full_name: String (materialized path)
- type: Enum [ASSET, LIABILITY, EQUITY, INCOME, EXPENSE]
- commodity: String (ISO 4217 currency code)
- description: Text
- hidden: Boolean
- placeholder: Boolean
- created_at: DateTime
- updated_at: DateTime
```

#### Transaction
```
- id: UUID
- tenant: ForeignKey(Tenant)
- guid: UUID (GnuCash-compatible)
- entry_date: Date
- post_date: Date
- description: String
- notes: Text
- created_at: DateTime
- updated_at: DateTime
- created_by: ForeignKey(User)
```

#### Split
```
- id: UUID
- tenant: ForeignKey(Tenant)
- transaction: ForeignKey(Transaction)
- account: ForeignKey(Account)
- value: Decimal (signed, positive=debit, negative=credit)
- quantity: Decimal (for non-currency commodities)
- memo: String
- reconciled: Enum [NONE, CLEARED, RECONCILED]
- created_at: DateTime
```

#### Budget
```
- id: UUID
- tenant: ForeignKey(Tenant)
- name: String
- start_date: Date
- end_date: Date
- style: Enum [TRADITIONAL, ENVELOPE]
- rollover: Boolean (for envelope style)
- created_at: DateTime
```

#### BudgetCategory
```
- id: UUID
- budget: ForeignKey(Budget)
- account: ForeignKey(Account)
- amount: Decimal
- notes: Text
```

#### Asset
```
- id: UUID
- tenant: ForeignKey(Tenant)
- account: ForeignKey(Account)
- name: String
- description: Text
- purchase_date: Date
- purchase_value: Decimal
- current_value: Decimal
- last_valuation_date: Date
```

#### InvestmentAccount
```
- id: UUID
- tenant: ForeignKey(Tenant)
- account: ForeignKey(Account)
- institution: String
- account_number: String
```

#### InvestmentLot
```
- id: UUID
- tenant: ForeignKey(Tenant)
- account: ForeignKey(InvestmentAccount)
- security_id: String
- quantity: Decimal
- purchase_date: Date
- purchase_price: Decimal
- cost_basis: Decimal
```

#### Receipt
```
- id: UUID
- tenant: ForeignKey(Tenant)
- transaction: ForeignKey(Transaction, nullable)
- file_url: String (Cloudflare R2)
- ocr_text: Text
- vendor: String
- total_amount: Decimal
- receipt_date: Date
- status: Enum [PENDING, PROCESSED, MANUAL_REVIEW]
- auto_category: ForeignKey(Account, nullable)
- user_category: ForeignKey(Account, nullable)
- created_at: DateTime
```

#### RecurringTransaction
```
- id: UUID
- tenant: ForeignKey(Tenant)
- template: JSON (transaction structure)
- frequency: Enum [DAILY, WEEKLY, MONTHLY, QUARTERLY, YEARLY]
- start_date: Date
- end_date: Date (nullable)
- last_run: DateTime (nullable)
- next_run: Date
- enabled: Boolean
```

#### AuditLog
```
- id: UUID
- tenant: ForeignKey(Tenant)
- user: ForeignKey(User, nullable)
- action: Enum [CREATE, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT]
- model: String
- object_id: UUID
- old_values: JSON (nullable)
- new_values: JSON (nullable)
- ip_address: String
- user_agent: String
- timestamp: DateTime
```

#### Notification
```
- id: UUID
- tenant: ForeignKey(Tenant)
- user: ForeignKey(User)
- type: String
- title: String
- body: Text
- read: Boolean
- created_at: DateTime
```

#### NotificationPreference
```
- id: UUID
- user: ForeignKey(User)
- notification_type: String
- channel_in_app: Boolean
- channel_email: Boolean
- channel_push: Boolean
```

### 3.2 Multi-Tenancy Implementation

- All models (except User) include `tenant: ForeignKey(Tenant)`
- `django-multitenant` for automatic query scoping
- PostgreSQL Row Level Security policies as defense in depth

```sql
-- Example RLS policy
CREATE POLICY tenant_isolation ON accounts
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

---

## 4. Feature Specifications

### 4.1 Account Management

**Capabilities:**
- Create, edit, delete accounts
- Hierarchical structure (unlimited depth)
- Account types: Asset, Liability, Equity, Income, Expense
- Multi-currency support (per-account currency)
- Account color coding
- Hide placeholder accounts

**Validation:**
- Account type cannot change after transactions exist
- Cannot delete accounts with transactions (must mark hidden)

### 4.2 Transaction Entry

**Multi-Split Form:**
- Add/remove splits dynamically
- Real-time balance validation (sum must = 0)
- Date picker for entry/post dates
- Memo/notes field
- Auto-complete for payees

**Keyboard Shortcuts:**
- `Ctrl+S`: Save transaction
- `Ctrl+N`: New transaction
- `Escape`: Cancel/close

**Auto-Categorization:**
- ML model suggests accounts based on payee/memo
- Learns from user corrections
- Confidence threshold for auto-apply

### 4.3 Receipt Capture

**Flow:**
1. User uploads receipt (image/PDF)
2. Cloud OCR extracts text (AWS Textract / Google Vision)
3. Parse vendor, date, total, line items
4. Suggest expense category based on learned patterns
5. User confirms or corrects
6. Create transaction (optional)
7. Store correction as training data

**ML Model:**
- Initial: Rule-based (vendor name → category mapping)
- Evolved: Embedding-based similarity matching
- Training data: User corrections stored as `(vendor, text, category)` tuples

### 4.4 Budget Management

**Traditional Budget:**
- Set monthly limit per category
- Track budgeted vs. actual
- No rollover of unused amounts

**Envelope Budget:**
- Allocate funds to envelopes (categories)
- Spending reduces envelope balance
- Unused balance rolls to next month
- Can overspend (negative envelope)

**Budget Views:**
- Monthly calendar view
- Category breakdown chart
- Progress bars (spent/remaining)

### 4.5 Investment Tracking

**Securities:**
- Stocks, bonds, mutual funds
- Price updates via free API (Yahoo Finance, Alpha Vantage)
- Manual price entry

**Lot Tracking:**
- Track individual purchase lots
- FIFO, LIFO, specific-lot selection for sales
- Cost basis calculation

**Corporate Actions:**
- Stock splits (auto-adjust lots)
- Dividends (cash or reinvestment)
- Mergers/acquisitions (manual adjustment)

### 4.6 Reports

**Balance Sheet:**
- Assets = Liabilities + Equity
- Snapshot at point in time
- Compare to prior period

**Income Statement (P&L):**
- Income - Expenses = Net Income
- Date range selectable
- Compare to budget

**Cash Flow Statement:**
- Operating, Investing, Financing activities
- Indirect method (from balance sheet changes)

**Account Register:**
- Filterable transaction list
- Export to CSV/PDF
- Reconciliation toggles

**Budget vs. Actual:**
- Per-category comparison
- Variance calculation
- Visual charts

**Net Worth Over Time:**
- Trend graph (Assets - Liabilities)
- Configurable time range

### 4.7 Account Reconciliation

**Flow:**
1. User enters statement end date + ending balance
2. System shows unreconciled transactions up to end date
3. Auto-suggest matches (amount + date proximity)
4. User marks transactions as cleared
5. System calculates difference
6. When balanced, mark as reconciled

**Auto-Suggest Algorithm:**
- Match by amount (exact or within tolerance)
- Prioritize by date proximity to statement date
- Learn from user confirmations

### 4.8 Recurring Transactions

**Templates:**
- Full transaction structure (splits, memos)
- Frequency: daily, weekly, monthly, quarterly, yearly
- Start/end dates or indefinite
- Next run date calculation

**Execution:**
- Celery beat scheduled task
- Create transaction on run date
- Skip weekends/holidays (configurable)
- Notify user before/after (configurable)

### 4.9 Offline Support

**PWA Features:**
- Service Worker for app shell caching
- IndexedDB for local data storage
- Sync queue for offline mutations

**Sync Protocol:**
1. On reconnect, pull server changes since last sync
2. Push queued mutations
3. Detect conflicts (same record modified)
4. Prompt user to resolve conflicts

**Conflict Resolution:**
- Show both versions side-by-side
- User selects which to keep, or manual merge
- Log conflict for audit trail

### 4.10 Notifications

**Types:**
- Recurring transaction即将 fire (configurable advance notice)
- Budget threshold exceeded (80%, 100%)
- Receipt needs manual review
- Reconciliation reminder
- Billing alerts (trial ending, payment failed)
- Security alerts (new login, password change)

**Channels:**
- In-app notification bell
- Email (Postmark/SendGrid)
- Push notifications (Web Push API)

**User Preferences:**
- Per-notification-type channel selection
- Quiet hours configuration
- Digest vs. instant delivery

### 4.11 Audit Logging

**Logged Actions:**
- All CRUD operations on transactions, accounts
- Login/logout events
- Data exports
- Setting changes

**Retention:**
- Configurable per tenant (default: 7 years)
- Auto-delete via Celery beat task

**User Access:**
- Users can view their tenant's audit log
- Filter by date, user, action type
- Admin hub can query across tenants

### 4.12 Authentication

**Methods:**
- Email/password (Argon2 hashing)
- 2FA (TOTP via Google Authenticator, Authy)
- Social login (Google, Apple, Microsoft)

**Session Management:**
- Device list in user settings
- Revoke individual sessions
- Force logout all devices

**Security:**
- Password strength requirements
- Rate limiting on login attempts
- Account lockout after N failed attempts

### 4.13 Billing

**Pricing:**
- Per-user/month (configurable price)
- 14-30 day free trial
- No feature tiers

**Stripe Integration:**
- Customer creation on tenant signup
- Subscription with metered billing (per active user)
- Webhooks for payment events
- Dunning management (failed payment retries)

### 4.14 Data Import/Export

**Import:**
- CSV with column mapping
- Save import templates per bank
- GnuCash `.gnucash` XML import (post-MVP)
- OFX/QFX import (post-MVP)

**Export:**
- CSV (all scopes)
- OFX/QFX (post-MVP)
- GnuCash XML (post-MVP)
- PDF reports

---

## 5. Frontend Architecture

### 5.1 Tenant App Routes

```
/                       → Dashboard (net worth, recent transactions)
/accounts               → Account list
/accounts/:id           → Account register/view
/transactions           → Transaction list
/transactions/new       → New transaction form
/transactions/:id       → Transaction detail/edit
/budgets                → Budget list
/budgets/:id            → Budget detail
/investments            → Investment portfolio
/receipts               → Receipt capture/list
/recurring              → Recurring transactions
/reports                → Report selection
/reports/balance-sheet  → Balance Sheet report
/reports/income-statement → P&L report
/reports/cash-flow      → Cash Flow report
/settings               → Tenant settings
/settings/users         → User management
```

### 5.2 Admin Hub Routes

```
/admin/dashboard        → Platform overview
/admin/tenants          → Tenant management
/admin/users            → User management
/admin/billing          → Stripe dashboard integration
/admin/support          → Support tickets
/admin/analytics        → Platform analytics
/admin/audit            → Cross-tenant audit log
```

### 5.3 Component Library

- **shadcn/ui** for base components (Button, Input, Dialog, etc.)
- **Radix UI** for complex primitives (ComboBox, DatePicker)
- **Custom components** for accounting-specific UI (SplitInput, AccountPicker)

### 5.4 State Management

- **React Query** for server state (caching, background sync)
- **Zustand** for client state (UI state, offline queue)
- **React Hook Form** for form handling

---

## 6. Backend Architecture

### 6.1 API Endpoints (v1)

```
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/register
POST   /api/v1/auth/2fa/enable
POST   /api/v1/auth/2fa/verify

GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/:id
PUT    /api/v1/accounts/:id
DELETE /api/v1/accounts/:id
GET    /api/v1/accounts/:id/register

GET    /api/v1/transactions
POST   /api/v1/transactions
GET    /api/v1/transactions/:id
PUT    /api/v1/transactions/:id
DELETE /api/v1/transactions/:id

GET    /api/v1/budgets
POST   /api/v1/budgets
GET    /api/v1/budgets/:id
PUT    /api/v1/budgets/:id
DELETE /api/v1/budgets/:id

GET    /api/v1/receipts
POST   /api/v1/receipts
GET    /api/v1/receipts/:id
DELETE /api/v1/receipts/:id
POST   /api/v1/receipts/:id/process

GET    /api/v1/recurring
POST   /api/v1/recurring
PUT    /api/v1/recurring/:id
DELETE /api/v1/recurring/:id

GET    /api/v1/reports/balance-sheet
GET    /api/v1/reports/income-statement
GET    /api/v1/reports/cash-flow
GET    /api/v1/reports/net-worth

GET    /api/v1/notifications
PUT    /api/v1/notifications/:id/read
GET    /api/v1/notifications/preferences
PUT    /api/v1/notifications/preferences

GET    /api/v1/audit-log

POST   /api/v1/imports/csv
POST   /api/v1/exports/csv
POST   /api/v1/exports/pdf
```

### 6.2 Background Tasks (Celery)

```
receipts.process_ocr(receipt_id)
receipts.learn_from_correction(receipt_id, user_category)
recurring.run_scheduled_transactions()
notifications.send_digest(user_id)
reports.generate_pdf(report_type, params)
billing.sync_stripe_data()
audit.purge_old_logs(retention_days)
```

---

## 7. Security

### 7.1 Authentication

- JWT access tokens (15 min expiry)
- Refresh tokens (7 day expiry, HttpOnly cookie)
- 2FA required for production tenants

### 7.2 Authorization

- Tenant isolation enforced at ORM layer (django-multitenant)
- PostgreSQL RLS as defense in depth
- Permission checks on all endpoints

### 7.3 Data Protection

- HTTPS everywhere (Let's Encrypt)
- Argon2 password hashing
- Encryption at rest for sensitive data (2FA secrets)
- Secrets in environment variables

### 7.4 Audit & Compliance

- All mutations logged
- Data export includes audit trail
- GDPR compliance (right to deletion, data portability)

---

## 8. Testing Strategy

### 8.1 Backend Tests

- **Unit tests:** Models, services, utilities
- **Integration tests:** API endpoints, Celery tasks
- **Property-based tests:** Double-entry invariants
- **Security tests:** Tenant isolation, auth bypass attempts

### 8.2 Frontend Tests

- **Unit tests:** Components, hooks, utilities
- **Integration tests:** Forms, workflows
- **E2E tests:** Playwright (critical user journeys)

### 8.3 Critical Invariants

```python
# Every transaction must balance
assert sum(split.value for split in transaction.splits) == 0

# Tenant isolation
assert split.account.tenant == split.transaction.tenant

# Audit log immutability
assert not AuditLog.objects.filter(id=log.id).can_be_deleted()
```

---

## 9. Deployment

### 9.1 Infrastructure

- **VPS:** Ubuntu 22.04 LTS
- **Web server:** Nginx (reverse proxy, SSL termination)
- **App server:** Gunicorn (Django)
- **Task queue:** Celery + Redis
- **Database:** PostgreSQL 15+
- **File storage:** Cloudflare R2

### 9.2 CI/CD

- **GitHub Actions** for CI
- Automated testing on PR
- Deploy on merge to main
- Database migrations via GitHub Actions

### 9.3 Backups

- **Database:** Daily pg_dump to S3-compatible storage
- **Files:** Cloudflare R2 has built-in redundancy
- **Backup testing:** Monthly restore drills

---

## 10. Performance Targets

| Metric | Target |
|--------|--------|
| Page load (first paint) | < 2s |
| Transaction save | < 500ms |
| Report generation | < 3s (simple), < 10s (complex) |
| OCR processing | < 30s (async, user notified) |
| API p95 latency | < 200ms |
| Concurrent users (MVP) | 1,000 |

---

## 11. Out of Scope (Post-MVP)

- Bank sync via aggregators (Salt Edge, Plaid)
- GnuCash `.gnucash` file import
- OFX/QFX import/export
- Multi-language support (i18n)
- VAT/sales tax tracking
- Business features (invoicing, A/R, A/P)
- Mobile apps (iOS/Android)

---

## 12. Open Questions

| Question | Decision Needed |
|----------|-----------------|
| Audit log retention default | 7 years recommended |
| Free trial length | 14 vs. 30 days |
| OCR provider | AWS Textract vs. Google Vision |
| Exchange rate API | exchangerate-api.com vs. frankfurter.app |
| Email provider | Postmark vs. SendGrid |

---

## Appendix A: Glossary

- **Tenant:** A customer organization (individual or household)
- **Split:** A single line item in a transaction (debit or credit)
- **Commodity:** Currency or other tradable unit (stock, mutual fund)
- **Reconciliation:** Matching account records against external statements
- **Envelope budgeting:** Allocating funds to categories with rollover
