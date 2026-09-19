# Current State

**Status:** IDLE

**Last Updated:** 2026-09-19T13:26:04Z

**Last Session Summary:** Made the reimagined tree actually run. It had never been executed — it could not be, because a phantom `decimal-converter` dependency made `pip install` impossible and a missing `Decimal` import in `apps/accounting/models/fiscal.py` killed `django.setup()`. After provisioning an environment at `~/.venvs/gnucash-reimagined` and repairing both, plus 7 initial migrations and the ADR-010 trigger migration, the suite collects cleanly at 186 tests and runs on real PostgreSQL 16.15: **120 passed, 66 failed** (baseline was 80/89, and before that, nothing ran at all). Golden accounting is **40/40**, business documents **15/15**, reporting **18/18**. Phase E.1's models-and-services migration turned out to be materially incomplete — services and support modules were dropped during consolidation — and this session repaired the accounting, business-documents and reporting halves of that. Identity services and the document-intelligence test structure remain.

**Branch / HEAD:** `modernization/reimagine-scaffold` @ `6af43d13cb` — local branch, no upstream tracking, **not pushed**. Working tree is **dirty**: 64 changed paths (14 modified production files, 7 new migration directories, new service modules across reporting / identity / document_intelligence, and the restructured `tests/` tree).

**Workstream:** `modernization`

**Build state:** The **reimagined Django tree** was verified this session and is the authoritative result: `~/.venvs/gnucash-reimagined/bin/python -m pytest` → 186 collected, 120 passed, 66 failed, on PostgreSQL 16.15. Migrations apply cleanly to an empty database and reverse cleanly. The **upstream GnuCash C/C++ tree was NOT built or tested this session** — do not carry forward any build pass for it. Its last verified result remains the 2026-09-18 preflight: at HEAD `fb2c773bf6` with a clean tree, `ninja` completed 845/845 targets and `ninja check` ran 133 tests with 131 passing; the two failures were `test-qof` and `test-gnc-numeric`, never diagnosed (T-0008).

Environment: dependencies are installed at `~/.venvs/gnucash-reimagined` (Django 5.2.17, pytest 8.4.2, psycopg 3.3.6). **The repo has no venv of its own** — `.venv` is not gitignored, so an in-repo venv would dirty the tree. PostgreSQL 16.15 runs locally with `postgres`/`postgres`; **docker is not installed**, so `compose.yml` cannot be used.

Test database: `config/settings/test.py` points at `gnucash_test`, created and dropped by pytest. Do not create it by hand — a pre-existing `gnucash_test` makes pytest report "database already exists" and masks the real run.

**Focus:** Resuming Phase E.1 after a rate-limit abort — first proving the tree could execute at all, then closing gaps in the accounting golden suite, the ADR-010 database-level immutability requirement, and business-documents posting.

**Next:** **T-0010** — implement the three stub identity services (`authentication.py`, `authorization.py`, `tenant_service.py` are all `raise NotImplementedError`, and their method names do not match their own contract tests). That is 41 of the 66 remaining failures, and the last major Phase E.1 criterion-3 gap. Port behaviour from `identity-access/identity_access/domain/services/`, adapting to the unified flat `services/` package.

**Pending Human Action:**

- **T-0007** — confirm the reimagine track is the live plan and the same-stack uplift brief is dormant. Both are on disk claiming approval.
- **Q-0001** — confirm whether `borrowed/` plus `contrib/` are the off-limits trees. Proposed by the assistant, never answered.
- **Q-0002** — sign off the five medium-confidence P0 business rules before they are frozen as regression contracts.
- **Q-0003** — decide whether `DocumentPostingService` should own the draft→posted transition or leave it to the caller. Currently the caller does it, matching the legacy contract, and all 15 tests pass; changing it means editing a test.

**Known Blockers:**

| ID | Item | Owner | Blocks | Status |
|----|------|-------|--------|--------|
| B-0002 | 25 of 32 document-intelligence acceptance tests subclass `unittest.TestCase` while taking pytest fixtures, so pytest cannot inject them. Structural — no implementation work fixes it. Pre-existing in the legacy tree. | us | criterion 6 | open |
| B-0003 | RLS is unprovisioned: no SQL functions, no policies, no migration. `docker/init-db.sql` is the only definition and nothing applies it. `common/rls/` holds only `models.py`. | us | criterion 4, RLS tests | open |
| B-0004 | `docker/init-db.sql` declares `get_current_user_id()` / `get_current_entity_id()` as `RETURNS integer` while every PK is a UUID; the cast fails and `EXCEPTION WHEN OTHERS THEN RETURN NULL` swallows it, so RLS policies would read NULL silently. | us | B-0003 | open |

**Decisions passed:**

- 2026-09-19 — `DocumentLine.project` stays **removed**; do NOT restore or invent `accounting.Project`. The phantom FK pointed at a model that never existed in any tree, was referenced by nothing, and blocked `makemigrations` outright. Project / cost-centre / department / location tracking is intended to arrive as one generalised **Dimension** model, designed deliberately, not pre-empted by a bespoke Project. (F-0003)
- 2026-09-19 — Tenant context is centralised in `common/middleware/tenant.py` as the **single authoritative implementation**, extended with `TenantContext`, `tenant_context()`, `TenantContextManager` and `get_current_tenant_id` / `get_current_user_id` / `get_current_entity_id`. Apps may re-export it (reporting's `middleware.py` is a shim only) but must not reimplement tenancy. `identity_access.infrastructure.tenant_context` is not restored.
- 2026-09-19 — Posted-journal immutability is enforced in PostgreSQL (`accounting/0003_adr010_posted_immutability.py`), not only in the ORM. The policy is an **allow-list of mutable columns** compared via whole-row `to_jsonb(OLD)` minus those keys, so columns added later are protected by default. Only `updated_at` is mutable on a posted entry; `updated_at`, `reconcile_status`, `date_reconciled` and `online_id` on a posted line — reconciliation happens *after* posting and must stay writable. `BEFORE INSERT` is guarded on lines because adding a line to a posted entry changes the financial result as much as editing one.
- 2026-09-19 — BR-BUS-002 (invoice amounts stored positive) is enforced by DB `CheckConstraint`s on `DocumentLine` (`quantity > 0`, `unit_price >= 0`), **not** field validators, because `DocumentLine.save()` does not call `full_clean()`. Note the extracted rule names *conversion* as its "When" but *storage* as its "Then"; this resolved toward enforcement and is revisitable.
- 2026-09-19 — The modernization track is gated on the accounting golden suite: golden must be green before dependent business-document posting work proceeds. It is now green (40/40 on PostgreSQL).
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
