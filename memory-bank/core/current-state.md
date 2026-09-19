# Current State

**Status:** IDLE

**Last Updated:** 2026-09-19T14:11:07Z

**Last Session Summary:** Document posting became one atomic domain operation and the three stub identity services were implemented against their contract tests. `DocumentPostingService.post_document()` now locks the document, re-validates against the locked row, posts through the accounting engine, marks the document posted and writes the audit event inside one `transaction.atomic` block — deliberately replacing the legacy two-step caller contract that left a window where a posted `JournalEntry` could coexist with a document still reading DRAFT. `AuthenticationService`, `AuthorizationService` and `TenantService` now implement every method their contract tests call. Two adjacent defects were fixed: `AdvisorAccessGrant.revoke()`'s parameter name (which no acceptance test could ever have satisfied) and `ApiToken._generate_token()` producing a token longer than its own column, which made `ApiToken.objects.create()` impossible. The suite moved from **120 passed / 66 failed** to **148 passed / 38 failed**, with identity going 24/65 → 52/65. Every remaining failure is accounted for: 13 identity REST endpoints and 25 document-intelligence tests blocked by B-0002's structural defect. Per the user's standing rule, the atomicity guarantee is by construction and was **not** proven by a rollback test.

**Branch / HEAD:** `modernization/reimagine-scaffold`. The session's **work commit** — the one carrying all of this session's code — is `2b638a4948` ("Own the document posting lifecycle; implement the identity services", 8 files, +526/−47). **Every commit above `2b638a4948` contains only `memory-bank/` files**: they are bookkeeping for this handoff, not code, and their number will vary. To see exactly the tree this session verified, check out `2b638a4948`. All of it is pushed to `origin` (`faizel-noorgat/gnucash`); `origin/stable` remains at upstream `fb2c773bf6`, untouched.

**Note on this file's history:** at the start of this session it still recorded `6af43d13cb` as HEAD with a dirty tree, which was stale — the work had already been committed and pushed as `1f8972b30e`. That stale line was corrected during the session. Record the *work* commit and say explicitly which commit the Memory Bank itself lives in; do not record a bare HEAD sha that the very next commit will invalidate.

**Workstream:** `modernization`

**Build state:** The **reimagined Django tree** was verified this session at work commit `2b638a4948` with a clean tree, running from `modernized/gnucash-reimagined/`:

```
~/.venvs/gnucash-reimagined/bin/python -m pytest -q
→ 186 collected, 148 passed, 38 failed, on PostgreSQL 16.15
```

Per suite: accounting **56/56**, business_documents **15/15**, reporting **18/18**, identity **52/65**, document_intelligence **7/32**. A targeted `pytest tests/business_documents tests/accounting` run after the posting change returned 71 passed. The 38 failures are exactly T-0015 (13) plus B-0002 (25) — nothing else.

The **upstream GnuCash C/C++ tree was NOT built or tested this session**. Its last verified result remains the 2026-09-18 preflight: at HEAD `fb2c773bf6` with a clean tree, `ninja` completed 845/845 targets and `ninja check` ran 133 tests with 131 passing; the two failures were `test-qof` and `test-gnc-numeric`, never diagnosed (T-0008).

Environment: dependencies at `~/.venvs/gnucash-reimagined` (Django 5.2.17, pytest 8.4.2, psycopg 3.3.6). **The repo has no venv of its own** — `.venv` is not gitignored, so an in-repo venv would dirty the tree. PostgreSQL 16.15 runs locally with `postgres`/`postgres`; **docker is not installed**, so `compose.yml` cannot be used and `docker/init-db.sql` never runs.

Test database: `config/settings/test.py` points at `gnucash_test`, created and dropped by pytest. Do not create it by hand — a pre-existing `gnucash_test` makes pytest report "database already exists" and masks the real run.

**Focus:** Owning the document posting lifecycle, then T-0010 — implementing the three stub identity services.

**Next:** **T-0015** — build the identity REST layer. 13 tests in `tests/identity/integration/test_api.py` plus `test_users_must_authenticate_before_accessing_tenant_resources` fail purely because the endpoints do not exist (`/api/v1/auth/me/`, login, register, tenant list/get/create, membership invite/list, notification list/unread-count). The service layer beneath them is implemented and green, so this is serializers + viewsets + routes over working services, worth 13 tests.

**Pending Human Action:**

- **T-0007** — confirm the reimagine track is the live plan and the same-stack uplift brief is dormant. Both are on disk claiming approval.
- **Q-0001** — confirm whether `borrowed/` plus `contrib/` are the off-limits trees. Proposed by the assistant, never answered.
- **Q-0002** — sign off the five medium-confidence P0 business rules before they are frozen as regression contracts.
- **Q-0004** — decide how a role's permission set narrows to a legal entity. Until this is settled, `get_user_permissions` and the `has_permission` / `user_has_permission` duplication cannot be resolved.

**Known Blockers:**

| ID | Item | Owner | Blocks | Status |
|----|------|-------|--------|--------|
| B-0002 | 25 of 32 document-intelligence acceptance tests subclass `unittest.TestCase` while taking pytest fixtures, so pytest cannot inject them. Structural — no implementation work fixes it. Pre-existing in the legacy tree. | us | criterion 6 | open |
| B-0003 | RLS is unprovisioned: no SQL functions, no policies, no migration. `docker/init-db.sql` is the only definition and nothing applies it. `common/rls/` holds only `models.py`. | us | criterion 4, RLS tests | open |
| B-0004 | `docker/init-db.sql` declares `get_current_user_id()` / `get_current_entity_id()` as `RETURNS integer` while every PK is a UUID; the cast fails and `EXCEPTION WHEN OTHERS THEN RETURN NULL` swallows it, so RLS policies would read NULL silently. | us | B-0003 | open |

**Decisions passed:**

- 2026-09-19 — **Posting is one atomic domain operation.** `DocumentPostingService.post_document()` owns the complete lifecycle: lock → validate → post → mark posted → persist the journal reference → audit → commit once. The legacy two-step contract (`post_document()` then a caller-side `mark_posted()`) is deliberately **not** preserved, because it created a consistency window in which a `JournalEntry` was posted while the `AccountingDocument` remained DRAFT. This is an intentional improvement over legacy behaviour, not a compatibility regression. Callers must no longer mark the document posted themselves. (Resolves Q-0003.)
- 2026-09-19 — `AdvisorAccessGrant.revoke()`'s parameter is `revoked_by`, matching the field it sets and the BR-PRACTICE-002 acceptance contract. The legacy tree had the acceptance test calling `revoked_by=` against a model declaring `revoked_by_user=`, so that test could never have passed anywhere. One keyword was updated in `tests/identity/unit/test_models.py`; the assertions were left untouched. `ApiToken.revoke()` still takes `revoked_by_user` — tracked as F-0006.
- 2026-09-19 — `DocumentLine.project` stays **removed**; do NOT restore or invent `accounting.Project`. The phantom FK pointed at a model that never existed in any tree, was referenced by nothing, and blocked `makemigrations` outright. Project / cost-centre / department / location tracking is intended to arrive as one generalised **Dimension** model, designed deliberately, not pre-empted by a bespoke Project. (F-0003)
- 2026-09-19 — Tenant context is centralised in `common/middleware/tenant.py` as the **single authoritative implementation**, extended with `TenantContext`, `tenant_context()`, `TenantContextManager` and `get_current_tenant_id` / `get_current_user_id` / `get_current_entity_id`. Apps may re-export it (reporting's `middleware.py` is a shim only) but must not reimplement tenancy. `identity_access.infrastructure.tenant_context` is not restored.
- 2026-09-19 — Posted-journal immutability is enforced in PostgreSQL (`accounting/0003_adr010_posted_immutability.py`), not only in the ORM. The policy is an **allow-list of mutable columns** compared via whole-row `to_jsonb(OLD)` minus those keys, so columns added later are protected by default. Only `updated_at` is mutable on a posted entry; `updated_at`, `reconcile_status`, `date_reconciled` and `online_id` on a posted line — reconciliation happens *after* posting and must stay writable. `BEFORE INSERT` is guarded on lines because adding a line to a posted entry changes the financial result as much as editing one. There is **no bypass of any kind** and there must never be one.
- 2026-09-19 — BR-BUS-002 (invoice amounts stored positive) is enforced by DB `CheckConstraint`s on `DocumentLine` (`quantity > 0`, `unit_price >= 0`), **not** field validators, because `DocumentLine.save()` does not call `full_clean()`. Note the extracted rule names *conversion* as its "When" but *storage* as its "Then"; this resolved toward enforcement and is revisitable.
- 2026-09-19 — The modernization track is gated on the accounting golden suite: golden must be green before dependent business-document posting work proceeds. It is green (40/40 golden, 56/56 accounting on PostgreSQL).
- 2026-09-19 — An unconditional `pytest.xfail(...)` inside a test body is treated as a defect, not a skip: it silently disables every assertion below it. Two such calls were removed from `tests/business_documents/test_acceptance.py`, which is what exposed that `DocumentPostingService` was broken.
- 2026-09-19 — The four working trees (`.claude/`, `analysis/`, `memory-bank/core/`, `modernized/`) are **committed to the fork**, not excluded from git. Committed on branch `modernization/reimagine-scaffold` (`74374234d1`) rather than directly to `stable`, so `stable` stays clean against upstream. `memory-bank/runtime/` live state, `.claude/scheduled_tasks.lock`, and `__pycache__`/`*.pyc` stay ignored — runtime churn, not shared history. (Resolves D-0001.)
- 2026-09-19 — Session memory ported with two skills (`session-start`, `session-close`) rather than one multi-mode skill, matching the two Cursor commands 1:1.
- 2026-09-19 — Tracking axes adapted from py-hoarder's SDLC-phase × project-plan model to gnucash-native axes (workstream + build state). GnuCash has no phase plans or `prompts/` tree to track against.
- 2026-09-19 — `prompts/` and `docs/40-delivery/` deliberately excluded from the port; lessons learned live in `memory-bank/core/lessons-learned.md` instead.
- 2026-09-19 — Scratchpad tests ported from pytest to stdlib `unittest` so the suite adds no dependency to an upstream C/C++ project.
- 2026-09-18 — Forked to `faizel-noorgat/gnucash` (`origin`) with `Gnucash/gnucash` as `upstream`; `stable` was 641 ahead / 40 behind, so the fork was reset to `upstream/stable` and force-pushed. The pre-reset divergence came from unrelated history in the fork, not from this work.
- 2026-09-18 — Analysis scope: `bindings/*.i` counts as source (SWIG input), not generated code. Off-limits was proposed as `borrowed/` + `contrib/` — still unconfirmed (Q-0001).
- 2026-09-19 — Modernization target is a **greenfield multi-tenant cloud accounting SaaS**, not a same-stack uplift: Django + PostgreSQL + Celery + React/TypeScript, five bounded contexts (`identity`, `accounting`, `business_documents`, `document_intelligence`, `reporting`), delivered as a modular monolith with one Django app per context and REST only.
- 2026-09-19 — Rejected at design review: GraphQL, Django Channels/WebSockets, a separate AI service container, eight bounded contexts, full intercompany consolidation, and putting many client companies into one Tenant. A practice managing many clients is modelled explicitly (`Practice`, `PracticeMembership`, `ClientEngagement`, `AdvisorAccessGrant`), never by conflating tenants.
- 2026-09-19 — Multi-tenancy is shared-schema PostgreSQL with row-level security (`SET LOCAL`, transaction-local, fail-closed), not schema-per-tenant.
- 2026-09-19 — GnuCash's dual `amount` (account commodity) / `value` (transaction currency) fields are preserved, with trading accounts kept internally but hidden from the UI.
