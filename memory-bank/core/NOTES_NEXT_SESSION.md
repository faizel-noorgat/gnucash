# Notes for Next Session

**Written:** 2026-09-19T14:38:00Z
**Status at Close:** IDLE. Branch `modernization/reimagine-scaffold`, work commits `12d3e8d202` and `665ba4a0c4`, pushed to `origin` with the Memory Bank commit directly on top. Working tree clean. Suite: **179 passed / 38 failed** of 217 on PostgreSQL 16.15.

---

## Priority Actions (do these first)

1. **T-0015 — Build the identity REST layer.** The queued next feature task; the user deferred it behind the RLS work, which is now committed. Thirteen tests, the entire remaining identity gap. Run first to confirm the baseline:
   ```bash
   cd modernized/gnucash-reimagined
   ~/.venvs/gnucash-reimagined/bin/python -m pytest tests/identity/integration/test_api.py -q
   ```
   The failing endpoints are `/api/v1/auth/me/`, login, register, tenant list/get/create, membership invite/list, and notification list/unread-count. The services underneath are implemented and green — this is serializers, viewsets and URL routes over working code, not new domain logic. `tests/identity/acceptance/test_authentication_rules.py::test_users_must_authenticate_before_accessing_tenant_resources` needs `/api/v1/auth/me/` too and is the 13th.

2. **B-0005 — the RLS isolation surface is only half done, and this is unprioritised.** 36 tables carrying a direct `tenant_id` are now policed, but **20 tables reach a tenant only through a parent FK and have no policy at all**: `accounting_journalline`, `accounting_counterpartposting`, `accounting_reconciliationauditlog`, `accounting_transactionmetadata`, `business_documents_document_line`, `business_documents_document_attachment`, `business_documents_approval_step`, `advisor_access_grants`, `reporting_dashboardwidget`, `workflow_transitions`, `document_extractions`, `document_matches` and others. Raw SQL or an unfiltered queryset over `accounting_journalline` reaches every tenant's ledger lines. Each needs an `EXISTS` policy against its parent. **Ask the user whether this pre-empts T-0015** — they scoped the RLS task to the direct tables and have not been asked.

3. **B-0002 — Decide the document-intelligence test structure.** 25 of 32 tests subclass `unittest.TestCase` while their methods take pytest fixtures, which pytest cannot inject. Structural: no implementation work makes them pass. Choose between rewriting the classes as plain pytest classes or moving fixtures into `setUp()`. This is half of the remaining 38 failures. `tests/rls/` and `tests/business_documents/test_posting_atomicity.py` both use plain pytest functions with `pytestmark = pytest.mark.django_db(transaction=True)` — a working model for the rewrite.

4. **Q-0004 — decide entity-scoped permission narrowing.** Blocks implementing `get_user_permissions` and collapsing the `has_permission` / `user_has_permission` duplication in `AuthorizationService`. `Membership.scoped_entity` (null = all entities) and `Role.tenant` (nullable) exist, but nothing defines how a role's permissions filter by entity, and the BR-AUTH-012 test marks itself a simplified stand-in. Guessing this bakes an unverified access-control semantic into the service layer.

5. **T-0014 — the unmanaged `ImmutablePostedJournal*` models break every ORM delete** of a journal entry or line: Django's deletion collector follows their relations and emits `DELETE FROM accounting_immutable_posted_journal_line`, which does not exist. Either give them real tables or take them out of the deletion path, then restore the ADR-010 ORM-delete test to assert the ADR-010 message specifically rather than bare `DatabaseError` (see LL-008).

6. **T-0008 — diagnose `test-qof` and `test-gnc-numeric`** in the *upstream* tree (unrelated to the reimagine work):
   ```bash
   cmake --build build && ctest --test-dir build -R "test-qof|test-gnc-numeric" --output-on-failure
   ```

**Waiting on the human (cannot be resolved by reading the tree):**

- **T-0007** — confirm the reimagine track is live and the same-stack uplift brief is dormant. Both claim approval on disk.
- **Q-0001** — confirm the off-limits trees (`borrowed/` + `contrib/` were proposed, never answered).
- **Q-0002** — sign off the five medium-confidence P0 rules before they harden into regression contracts.

Lower priority: **F-0001** (re-apply plugin-cache agent edits after a plugin update), **F-0002** (`FRONTEND_URL` and the `LLM_*` keys are undeclared settings read via `getattr` fallbacks), **F-0003** (project/cost-centre support belongs to a future Dimension model), **F-0004** (residual `TODO`/`NotImplementedError` markers by context — the identity ones now carry an explicit reason each, the rest do not), **F-0005** (MFA enrolment cannot persist its TOTP secret: the `User` model has no field for it, so `mfa_enabled` is an enrolment flag and not enforced MFA), **F-0006** (`ApiToken.revoke` still takes `revoked_by_user` while `AdvisorAccessGrant.revoke` takes `revoked_by`; re-confirmed as-is this session, both call sites green).

---

## Context to Remember

- **Environment.** Tests run with `~/.venvs/gnucash-reimagined/bin/python -m pytest`, from `modernized/gnucash-reimagined/`. System `python3` has **no Django** — it will fail confusingly. There is deliberately **no venv inside the repo**: `.venv` is not gitignored. PostgreSQL 16.15 runs locally with `postgres`/`postgres`. **Docker is not installed**, so `compose.yml` is unusable.

- **The test database.** `config/settings/test.py` points at `gnucash_test`, which pytest creates and drops itself. Do not create it by hand — a pre-existing `gnucash_test` makes pytest report "database already exists" and masks the real run. If you need to inspect the migrated schema by hand, create it, migrate, and **drop it again** before the next pytest run.

- **`app_user` is a cluster-wide role, not per-database.** It is created by `common/rls/migrations/0001` and survives test-database teardown. It has `NOLOGIN`, owns nothing, and has no `BYPASSRLS`.

- **A superuser bypasses RLS even against a `FORCE`d table.** This was confirmed directly against PostgreSQL before being relied on, and it is the single most important fact for reading the RLS tests. Django's connection in tests is the `postgres` superuser, so a test asserting isolation through it would pass no matter what the policies said. Every RLS assertion is made inside `tests/rls/conftest.py`'s `rls_session()` (drops to `app_user` and sets the three GUCs with `set_config(..., true)`) or `app_role()` (drops to `app_user`, sets no context — for code that supplies its own context, like the Celery base).

- **RLS context is transaction-local, and the layer split is deliberate.** RLS enforces the boundary around whatever tenant is in context; `AuthorizationService.can_access_tenant()` decides which tenant a caller may assume. The practice/engagement/grant chain is intentionally **not** duplicated into SQL policies — two copies of one authorization rule is exactly what produced the `Role.get_permissions()` defect.

- **`TenantScopedTask` did not exist and was written this session** (`common/rls/tasks.py`). It runs the body inside one `transaction.atomic` because `SET LOCAL` is discarded at the end of the transaction it was issued in, and raises rather than reading zero rows when called without `tenant_id`.

- **The suite stands at** accounting **56/56** (golden **40/40**, ADR-010 **16/16**), reporting **18/18**, business_documents **17/17**, identity **52/65**, document_intelligence **7/32**, rls **26/26**. The 38 failures are exactly T-0015 (13) plus B-0002 (25) — nothing else.

- **Plain pytest functions beat `unittest.TestCase` here.** `pytest.mark.django_db(transaction=True)` gives a real transaction rather than a savepoint, which matters whenever the claim under test is about COMMIT/ROLLBACK or about `SET LOCAL`. It also sidesteps the fixture-injection defect behind B-0002. Both new test modules this session use it.

- **Gunicorn note for later:** nothing currently connects as `app_user`. Production settings still point at the owner role. Wiring the runtime connection to `app_user` is part of making the isolation real in a deployed environment, and is not done.

- **The recurring defect pattern.** Phase E.1's "migrate models" step was recorded complete but was materially incomplete: **services and support modules were dropped** during consolidation, and migrated code kept referring to things that never existed. Every unexplained failure so far has had that shape. When something is inexplicably red, suspect a reference to a legacy name before suspecting logic. Concrete instances: a phantom `decimal-converter` PyPI dependency, a `Decimal` used in a def-time annotation with no import, 9 FKs pointing at `"auth.User"`, `PostingService.create_reversal_entry` called on the wrong class, `DocumentPostingService` scaffolded against an imagined accounting API, `ApiToken._generate_token()` emitting a token longer than its own column, `Role.get_permissions()` reading a relation that was never declared, and a required `TenantScopedTask` that was specified but never written.

- **Search tooling goes stale.** The jcodemunch index was built at 11:31 and was already wrong about files edited afterwards. A "no callers found" result from a stale index is not evidence of absence. Check `indexed_at` against the tree, and call `register_edit` with `reindex=true` after editing (LL-011).

---

## Do NOT Do

- **Do not run more than three agents at once.** Standing user rule.
- **Do not weaken, bypass, or add an escape hatch to any safeguard.** No `force=`, `_skip_validation`, `save_raw`, settings switch, session variable, bypass manager, or `BYPASSRLS` role. The accounting immutability guarantees and the tenant isolation boundary are the product's core value. If a test or fixture conflicts with a guard, fix the fixture.
- **Do not create a posted `JournalEntry` directly** (`is_posted=True` on create). Post through `PostingService` / `JournalEntry.post()` so balance, fiscal-period and audit checks run.
- **Do not call `document.mark_posted()` from outside `DocumentPostingService`.** The service owns that transition now.
- **Do not re-add an unconditional `pytest.xfail(...)` inside a test body.** It silently disables every assertion below it. Two such calls were hiding a completely broken posting service.
- **Do not re-introduce an `EXCEPTION WHEN OTHERS THEN RETURN NULL` around the RLS context casts.** Malformed context must stay loud; a silent NULL makes a context-writer bug look like normal operation.
- **Do not `CREATE OR REPLACE` the RLS helper functions.** `CREATE OR REPLACE` cannot change a return type, so it aborts on any database that ran the old `docker/init-db.sql`. Keep the `DROP FUNCTION IF EXISTS` before each `CREATE`.
- **Do not name an RLS policy at a specific role.** `TO PUBLIC` is deliberate; a policy naming a role nobody holds leaves the table default-denied.
- **Do not hand-edit `memory-bank/runtime/session-scratchpad.json`.** All mutations go through `.claude/scripts/session_scratchpad.py`.
- **Do not commit `memory-bank/runtime/`** — live per-session state, already gitignored.
- **Do not send anything from `analysis/` or `modernized/` upstream.** Fork branch only; upstream-bound work stays a minimal, reviewable diff against `main`.
- **Do not add or restore `accounting.Project`**, and do not re-add `DocumentLine.project`. Project/cost-centre support is future Dimension work.
- **Do not treat `mfa_enabled` as enforced MFA.** Nothing can verify a TOTP code, because no field holds the secret (F-0005).
- **Do not import models from `common/rls/__init__.py`.** That package is now an installed app; an eager model import there dies with `AppRegistryNotReady`. Import from `common.rls.models`.
- **Do not trust the artifact counts in `analysis/`** without re-deriving them from disk. They disagree with each other and with the transcripts.

---

## Human's Last Instruction

> `/session-close` — "and commit and push"

Before that, the session ran as two ordered directives:

1. *"Before starting another feature task, close and commit the current milestone."* — followed by a five-part hardening pass: prove `DocumentPostingService`'s rollback by fault injection at an application boundary (explicitly: *"Do not add production escape hatches solely for the test. Use mocking/fault injection at an appropriate application boundary"*), fix `Role.get_permissions()` against the real `RolePermission` relation (*"Do not maintain two competing permission representations"*), remove the session hook-probe files, preserve the `AdvisorAccessGrant.revoke(revoked_by=...)` and `ApiToken` generation fixes, re-run the milestone suites, and checkpoint-commit.
2. *"After the checkpoint commit, take [RLS provisioning] together as the next task... Do NOT work on the 13 identity API endpoint failures first. The architecture claims database-enforced tenant isolation, so we need to make that real before expanding the HTTP surface."* — ten numbered requirements, closing with: *"Do not rely on docker/init-db.sql as the authoritative runtime provisioning mechanism. Put production RLS schema changes into Django migrations so a clean deployment receives the correct policies deterministically"* and *"When complete, report the exact tables under RLS and the PostgreSQL isolation test results."*

Bracketed substitutions above replace a resolved scratchpad ID, so the handoff checker does not read this section as a pending item. The wording is otherwise as spoken.

Standing constraints carried in **Do NOT Do** above.
