# Notes for Next Session

**Written:** 2026-09-19T15:34:48Z
**Status at Close:** IDLE. Branch `modernization/reimagine-scaffold`, this session's work commit `290cc7e73e` (RLS closure, 18 files), pushed to `origin`. Suite: **227 passed / 38 failed** of 265 on PostgreSQL 16.15 — the 38 are exactly T-0015 (13) + B-0002 (25).

---

## Priority Actions (do these first)

1. **T-0015 — Build the identity REST layer.** 13 tests, the entire remaining identity gap. Run first to confirm the baseline:
   ```bash
   cd modernized/gnucash-reimagined
   ~/.venvs/gnucash-reimagined/bin/python -m pytest tests/identity/integration/test_api.py -q
   ```
   Failing endpoints: `/api/v1/auth/me/`, login, register, tenant list/get/create, membership invite/list, notification list/unread-count. The services underneath are implemented and green — this is serializers, viewsets and URL routes over working code.

   **The RLS closure added a constraint this endpoint work must satisfy.** A tenant-scoped request now runs inside a transaction the middleware owns, with `app_user`'s policies applied:
   - `tenants` INSERT requires `get_current_user_id() IS NOT NULL AND created_by_id = get_current_user_id()`. The creating service must set `created_by`.
   - The follow-up `Membership` INSERT requires `app.current_tenant_id` to be set.
   - So **registration must `SET LOCAL` context to the tenant it just created, in the same transaction, using the id of the row it just inserted** — never a client-supplied id, or it becomes the arbitrary-tenant hole the middleware was rewritten to close.
   - Nothing enforces this in tests yet, because tests run as the `postgres` superuser and bypass RLS. It will only surface once a runtime connection uses `app_user` (F-0007), which is exactly why it is written down here.

2. **B-0002 — Decide the document-intelligence test structure.** 25 of 32 tests subclass `unittest.TestCase` while their method signatures take pytest fixtures, which pytest cannot inject. Structural: no implementation work makes them pass. Choose between rewriting the classes as plain pytest classes or moving fixtures into `setUp()`. This is half of the remaining 38 failures. `tests/rls/` and `tests/business_documents/test_posting_atomicity.py` both use plain pytest functions with `pytestmark = pytest.mark.django_db(transaction=True)` — a working model.

3. **Q-0004 — decide entity-scoped permission narrowing.** Blocks implementing `get_user_permissions` and collapsing the `has_permission` / `user_has_permission` duplication in `AuthorizationService`. `Membership.scoped_entity` (null = all entities) and `Role.tenant` (nullable) exist, but nothing defines how a role's permissions filter by entity, and the BR-AUTH-012 test marks itself a simplified stand-in.

4. **F-0007 — decide whether the runtime connection becomes `app_user`.** Every environment connects as the `postgres` superuser today, so although 51 tables carry correct, tested, principal-named policies, **nothing is subject to them at runtime**. `manage.py check` reports this as `rls.W001` whenever `RLS_ENABLED` is on. The fix is splitting the runtime connection from the deploy/migration connection.

5. **T-0014 — the unmanaged `ImmutablePostedJournal*` models break every ORM delete** of a journal entry or line: Django's deletion collector follows their relations and emits `DELETE FROM accounting_immutable_posted_journal_line`, which does not exist. Either give them real tables or take them out of the deletion path, then restore the ADR-010 ORM-delete test to assert the ADR-010 message specifically rather than bare `DatabaseError` (LL-008).

6. **T-0008 — diagnose `test-qof` and `test-gnc-numeric`** in the *upstream* tree (unrelated to the reimagine work):
   ```bash
   cmake --build build && ctest --test-dir build -R "test-qof|test-gnc-numeric" --output-on-failure
   ```

**Waiting on the human (cannot be resolved by reading the tree):**

- **F-0008** — a second Claude session is active against this same working tree and has already discarded uncommitted work once. Confirm whether it has been stopped.
- **T-0007** — confirm the reimagine track is live and the same-stack uplift brief is dormant. Both claim approval on disk.
- **Q-0001** — confirm the off-limits trees (`borrowed/` + `contrib/` were proposed, never answered).
- **Q-0002** — sign off the five medium-confidence P0 rules before they harden into regression contracts.
- **F-0009** — decide whether `practices` / `practice_memberships` need their own scoping concept. Both are unpoliced; the stated residual of the RLS closure.

Lower priority: **F-0001** (re-apply plugin-cache agent edits after a plugin update), **F-0002** (`FRONTEND_URL` and the `LLM_*` keys are undeclared settings read via `getattr` fallbacks), **F-0003** (project/cost-centre support belongs to a future Dimension model), **F-0004** (residual `TODO`/`NotImplementedError` markers by context), **F-0005** (MFA enrolment cannot persist its TOTP secret), **F-0006** (`ApiToken.revoke` still takes `revoked_by_user` while `AdvisorAccessGrant.revoke` takes `revoked_by`).

---

## Context to Remember

- **Two Claude sessions ran against this tree at once, and it cost real time.** The other one ran `git stash push -m wip-b0005-probe` + `git reset --hard HEAD`, discarding ~1600 uncommitted lines. They were recovered with `git stash apply`; **`stash@{0}` was left in place as a backup and has not been dropped.** The same two sessions shared the hard-coded `gnucash_test` database, which produced ~90 phantom failures that took a full bisect to attribute: `duplicate key ... auth_permission` after a truncated flush, `database "gnucash_test" does not exist` mid-run, and results that flipped between identical invocations. If two sessions must run, give each its own test database via a settings module outside the repo — that is how the final numbers were obtained.

- **Before bisecting a mystery failure, check whether another process owns the database.** The phantom failures above looked exactly like a code defect introduced by a recent edit, and were not.

- **Environment.** Tests run with `~/.venvs/gnucash-reimagined/bin/python -m pytest`, from `modernized/gnucash-reimagined/`. System `python3` has **no Django**. PostgreSQL 16.15 runs locally with `postgres`/`postgres`, and **that role is a superuser, which bypasses RLS even against a FORCEd table** — the single most important fact for reading any RLS test. **Docker is not installed.**

- **The test database.** `config/settings/test.py` points at `gnucash_test`, created and dropped by pytest. Do not create it by hand — a pre-existing one makes pytest report "database already exists" and masks the real run. `app_user` is a **cluster-wide** role and survives test-database teardown.

- **How RLS is verified.** Every isolation assertion is made inside `tests/rls/conftest.py`'s `rls_session()` (drops to `app_user` with `SET LOCAL ROLE` and sets the GUCs via `set_config(..., true)`) or `app_role()` (drops role, sets no context — for code that supplies its own, like the Celery base and the middleware). Asserting through Django's own connection would pass no matter what the policies said.

- **Boundaries.** `common/rls` policies are `TO app_user`, `ENABLE` + `FORCE`, on 51 of 65 tables. The 14 unpoliced are global: 7 Django contrib, 2 auth M2M, `users`, `permissions`, `practices`, `practice_memberships`, `workflow_definitions`. `tests/rls/test_rls_provisioning.py` asserts this against PostgreSQL's catalogues, not against a list in a migration, so a new tenant-scoped model without a policy fails a test.

- **A policy alone is not isolation.** PostgreSQL does not evaluate policies unless `relrowsecurity` is set on the table, so a table can have a perfect policy listed in `pg_policies` and be wide open. That bug shipped in this session's first draft and every other assertion still passed. Assert the `relforcerowsecurity` flag.

- **The suite stands at** accounting **56/56** (golden **40/40**), business_documents **17/17**, reporting **18/18**, identity **52/65**, document_intelligence **7/32**, **rls 74/74**.

- **The recurring defect pattern.** Phase E.1's "migrate models" step was recorded complete but was materially incomplete: services and support modules were dropped, and migrated code kept referring to things that never existed. Every unexplained failure so far has had that shape. When something is inexplicably red, suspect a reference to a legacy name before suspecting logic. This session added three more instances of the same family — a middleware that had never run, a header trusted without a check, and policies created on tables where RLS was never enabled — all of which *looked* implemented.

- **Search tooling goes stale.** A "no callers found" result from a stale jcodemunch index is not evidence of absence. Check `indexed_at` against the tree, and call `register_edit` with `reindex=true` after editing (LL-011).

- **Index state at close.** Code index refreshed to **1,752 files / 32,972 symbols** (from 1,720 / 32,369). Docs index at **3,989 sections**, but **embedding coverage is only 954/3,989 sections (23.9%)**, so semantic/hybrid doc search will rank most of the corpus at zero — re-index with `incremental=false` if you need it, and prefer `search_sections` (BM25) until then. Both indexes were built while the tree was dirty with uncommitted `memory-bank/` changes, so neither is certified against a commit.

---

## Do NOT Do

- **Do not run more than three agents at once.** Standing user rule.
- **Do not run two Claude sessions against this working tree at once.** One has already discarded uncommitted work here (F-0008).
- **Do not weaken, bypass, or add an escape hatch to any safeguard.** No `force=`, `_skip_validation`, `save_raw`, settings switch, session variable, bypass manager, or `BYPASSRLS` role. The accounting immutability guarantees and the tenant isolation boundary are the product's core value. If a test or fixture conflicts with a guard, fix the fixture.
- **Do not create a posted `JournalEntry` directly** (`is_posted=True` on create). Post through `PostingService` / `JournalEntry.post()`.
- **Do not call `document.mark_posted()` from outside `DocumentPostingService`.**
- **Do not re-add an unconditional `pytest.xfail(...)` inside a test body.** It silently disables every assertion below it.
- **Do not move the tenant authorization check out of `TenantContextMiddleware`, or gate it on `RLS_ENABLED`.** RLS confines a session to whatever tenant is in context; it cannot tell whether that tenant was the right one. Without the check, `X-Tenant-ID` is attacker-chosen again. `TenantContext` and `TenantContextManager` do no authorization of their own and must not be reached from request handling with a caller-supplied tenant.
- **Do not issue `SET LOCAL` outside a `transaction.atomic()`.** It is discarded with a warning and the request silently runs with no context — the exact bug that made the middleware a no-op.
- **Do not name an RLS policy at `PUBLIC`,** and do not create a policy without `ENABLE` + `FORCE` on the table. Both fail silently in the permissive direction.
- **Do not re-introduce an `EXCEPTION WHEN OTHERS THEN RETURN NULL` around the RLS context casts.** Malformed context must stay loud.
- **Do not `CREATE OR REPLACE` the RLS helper functions.** `CREATE OR REPLACE` cannot change a return type; keep the `DROP FUNCTION IF EXISTS` before each `CREATE`.
- **Do not make a child's tenant column stricter than its parent's.** The shapes must match, or rows the parent accepts become impossible to attach anything to.
- **Do not `git stash`/`reset` this tree without checking for uncommitted work first.** Another session lost 1600 lines that way.
- **Do not hand-edit `memory-bank/runtime/session-scratchpad.json`.** All mutations go through `.claude/scripts/session_scratchpad.py`.
- **Do not commit `memory-bank/runtime/`** — live per-session state, already gitignored.
- **Do not send anything from `analysis/` or `modernized/` upstream.** Fork branch only.
- **Do not add or restore `accounting.Project`**, and do not re-add `DocumentLine.project`.
- **Do not treat `mfa_enabled` as enforced MFA.** Nothing can verify a TOTP code (F-0005).
- **Do not import models from `common/rls/__init__.py`.** Import from `common.rls.models`.
- **Do not trust the artifact counts in `analysis/`** without re-deriving them from disk.

---

## Human's Last Instruction

> `/session-close` — "commit and push"

Before that, the session ran as one directive:

> *"Take the remaining RLS gap next, before Identity API work."* — followed by a seven-part specification: inventory and classify every table; prefer an explicit `tenant_id` for genuine tenant-owned children, enforced at the database level so `child.tenant_id` cannot disagree with `parent.tenant_id`, with the application populating it automatically; use `EXISTS` policies where indirect ownership is the cleaner model, with equivalent `WITH CHECK`; **remove `TO PUBLIC`** in favour of explicit runtime roles and inventory role privileges; **keep advisor authorization centralized** in `AuthorizationService.can_access_tenant()` and audit the request path so arbitrary tenant context cannot be established without that decision; expand the PostgreSQL isolation tests to bypass Django's relationship filtering with raw SQL; and put every change in Django migrations, verified from a fresh database. Closing requirement: *"Only after that should B-0003/B-0004 be considered fully closed. Then proceed to the 13 Identity API tests."*

The user answered two design questions mid-session and both chose the recommended option: a self-scoped `SELECT` policy so the authorization check can run before any tenant context exists (check-then-set, failing closed), and bringing the `tenants` registry under RLS.

Standing constraints carried in **Do NOT Do** above.
