# Notes for Next Session

**Written:** 2026-09-19T19:20:36Z
**Status at Close:** IDLE. Branch `modernization/reimagine-scaffold`, work commit `9b0a6d6bcc`, bookkeeping commit `4857c38858`, both pushed. **Working tree clean** — the `.claude/` files that had been dirty since the RLS session are now committed. The session split the runtime and deploy database credentials and closed the item that tracked it.

---

## Priority Actions (do these first)

1. **T-0015 — build the identity REST layer.** 13 tests, the entire remaining identity gap. Confirm the baseline first:
   ```bash
   cd modernized/gnucash-reimagined
   ~/.venvs/gnucash-reimagined/bin/python -m pytest tests/identity/integration/test_api.py -q
   ```
   Missing endpoints: `/api/v1/auth/me/`, login, register, tenant list/get/create, membership invite/list, notification list/unread-count. The services underneath are implemented and green — this is serializers, viewsets and URL routes over working code.

   **Two constraints the RLS work imposes on this, and one correction.**
   - `tenants` INSERT requires `get_current_user_id() IS NOT NULL AND created_by_id = get_current_user_id()`.
   - The follow-up `Membership` INSERT requires `app.current_tenant_id`.
   - So **registration must `SET LOCAL` context to the tenant it just created, in the same transaction, using the id of the row it inserted** — never a client-supplied id, or it becomes the arbitrary-tenant hole the middleware was rewritten to close.
   - **The correction: the credential split did not make this testable**, which the previous handoff predicted it would. Django creates *and* migrates the test database through the connection the tests then run as, so the test session is still the `postgres` superuser (F-0010). Write any test meant to prove the bootstrap inside `rls_session()` / `app_role()` from `tests/rls/conftest.py`, or it will pass against an endpoint that never sets context.

2. **F-0009 — scope Practice and PracticeMembership visibility.** User directive: they are global platform entities, but they **must not remain generally enumerable**. Minimum is a policy on `practice_memberships` keyed to `user_id = get_current_user_id()`; if any callee needs a practice's full roster, introduce a practice-scoped GUC rather than widening the policy. Re-examine the advisor branch of `AuthorizationService.can_access_tenant()`, which joins through `practice_memberships`.

3. **F-0010 — decide how isolation-sensitive tests get the runtime role.** The test connection cannot be split from the migrating one, so a test that does not enter `rls_session()`/`app_role()` runs as a superuser and cannot see a missing tenant context. Either accept the convention, or stand up a path that migrates as the owner before pytest runs (a custom runner or a make target; Django tolerates a pre-created database, but `migrate` still needs DDL rights).

4. **F-0011 — production settings cannot be imported.** `config/settings/production.py` configures `pythonjsonlogger.jsonlogger.JsonFormatter`, which is not installed, so `DJANGO_SETTINGS_MODULE=config.settings.production` dies at `django.setup()`. Pre-existing. It means the production branch of the credential split is verified by reading rather than by loading, and no production deploy would boot.

5. **T-0018 — verify the Docker/compose startup path.** `compose.yml` was updated for the split (DB_* env, `migrate --database=deploy`, a documented one-time `ALTER ROLE app_user LOGIN`) and **none of it has been executed** — Docker is not installed. Confirm the ordering works when it can be run.

6. **B-0002 — decide the document-intelligence test structure.** 25 of 32 tests subclass `unittest.TestCase` while their method signatures take pytest fixtures, which pytest cannot inject. Structural: no implementation work makes them pass. Choose between rewriting the classes as plain pytest classes or moving fixtures into `setUp()`. `tests/rls/` and `tests/business_documents/test_posting_atomicity.py` both use plain pytest functions with `pytestmark = pytest.mark.django_db(transaction=True)` — a working model.

7. **Q-0004 — decide entity-scoped permission narrowing.** Blocks implementing `get_user_permissions` and collapsing the `has_permission` / `user_has_permission` duplication in `AuthorizationService`. `Membership.scoped_entity` (null = all entities) and `Role.tenant` (nullable) exist, but nothing defines how a role's permissions filter by entity, and the BR-AUTH-012 test marks itself a simplified stand-in.

8. **T-0014 — the unmanaged `ImmutablePostedJournal*` models break every ORM delete** of a journal entry or line: Django's deletion collector follows their relations and emits `DELETE FROM accounting_immutable_posted_journal_line`, which does not exist. Either give them real tables or take them out of the deletion path, then restore the ADR-010 ORM-delete test to assert the ADR-010 message specifically rather than bare `DatabaseError` (LL-008).

9. **T-0008 — diagnose `test-qof` and `test-gnc-numeric`** in the *upstream* tree (unrelated to the reimagine work):
   ```bash
   cmake --build build && ctest --test-dir build -R "test-qof|test-gnc-numeric" --output-on-failure
   ```

**Waiting on the human (cannot be resolved by reading the tree):**

- **F-0008** — a second Claude session has been active against this same working tree and has already discarded uncommitted work once. Decide whether to make the test database name derivable so concurrent runs cannot collide.
- **T-0007** — confirm the reimagine track is live and the same-stack uplift brief is dormant. Both claim approval on disk.
- **Q-0001** — confirm the off-limits trees (`borrowed/` + `contrib/` were proposed, never answered).
- **Q-0002** — sign off the five medium-confidence P0 rules before they harden into regression contracts.

Lower priority: **F-0001** (re-apply plugin-cache agent edits after a plugin update), **F-0002** (`FRONTEND_URL` and the `LLM_*` keys are undeclared settings read via `getattr` fallbacks), **F-0003** (project/cost-centre support belongs to a future Dimension model), **F-0004** (residual `TODO`/`NotImplementedError` markers by context), **F-0005** (MFA enrolment cannot persist its TOTP secret), **F-0006** (`ApiToken.revoke` still takes `revoked_by_user` while `AdvisorAccessGrant.revoke` takes `revoked_by`).

---

## Context to Remember

- **This machine's PostgreSQL cluster was changed this session, by explicit approval.** `CREATE DATABASE gnucash_dev OWNER postgres`, then `ALTER ROLE app_user LOGIN PASSWORD 'app_user'`. `gnucash_dev` **did not exist before** — development settings had been pointing at a database that was never created — so a dev run before this session could not have worked. `app_user` is **cluster-wide**; that password is a dev-only credential.

- **Migrations no longer run on `default` in development or production.** `default` is the RLS-bound runtime role, so:
  ```bash
  python manage.py migrate --database=deploy
  ```
  Running `migrate` without the alias fails with a permission error, by design.

- **Development now has `RLS_ENABLED = True`**, because `default` connects as `app_user`. With it off, the middleware issues no `SET LOCAL` and every tenant-scoped query returns zero rows. If local work suddenly shows empty result sets, suspect a missing tenant context rather than missing data — that is the boundary doing its job.

- **The two aliases are one database.** `split_databases()` in `config/settings/base.py` derives `default` and `deploy` from a single connection dict, so they cannot drift onto different servers. Only the credential differs. A test pins this.

- **`config/settings/test.py` is the one environment with a single `postgres` alias**, and it has to be — see F-0010 above. It is not an oversight and should not be "fixed" without solving the migrate-role problem first.

- **Roles are cluster-scoped; databases are not.** This is the trap that cost this session real time. A migration that re-asserts a role attribute runs **once per database**, and pytest creates a fresh one per run. Reproduced directly: grant `app_user` LOGIN, run `pytest tests/rls/test_rls_provisioning.py`, `rolcanlogin` is `false` again. `NOLOGIN` was removed from the re-asserting `ALTER ROLE` in `common/rls/migrations/0001` for exactly this reason; the four attributes that make the role safe to connect as are still re-asserted on every database.

- **Environment.** Tests run with `~/.venvs/gnucash-reimagined/bin/python -m pytest`, from `modernized/gnucash-reimagined/`. System `python3` has **no Django**. PostgreSQL 16.15 runs locally with `postgres`/`postgres`, and **that role is a superuser** — the single most important fact for reading any RLS test. **Docker is not installed**, so `compose.yml` is unverifiable here (T-0018).

- **The test database.** `config/settings/test.py` points at `gnucash_test`, created and dropped by pytest. Do not create it by hand. `app_user` survives test-database teardown, being cluster-wide.

- **How RLS is verified.** Every isolation assertion is made inside `tests/rls/conftest.py`'s `rls_session()` (drops to `app_user` with `SET LOCAL ROLE` and sets the GUCs via `set_config(..., true)`) or `app_role()`. Asserting through Django's own connection would pass no matter what the policies said.

- **Grep `APP_ROLE`, not `TO app_user`.** Policies are emitted as `TO {APP_ROLE}` from `APP_ROLE = "app_user"` in `common/rls/migrations/0004_tenant_isolation_closure.py`, so the literal string `TO app_user` appears nowhere in source. A grep for it returns zero and looks like a missing implementation.

- **`identity-access/`, `accounting-engine/`, `business-documents/`, `document-intelligence/` and `reporting-analytics/` are scaffold leftovers, not live code.** They are absent from `LOCAL_APPS` and nothing under `config/` references them. Their `settings/base.py` files also default to `app_user`, which is why a search for the role returns them first — **do not edit them thinking they are the application.** The live settings are `config/settings/`.

- **Boundaries.** `common/rls` policies are named to `app_user`, `ENABLE` + `FORCE`, on 51 of 65 tables. The 14 unpoliced are global: 7 Django contrib, 2 auth M2M, `users`, `permissions`, `practices`, `practice_memberships`, `workflow_definitions`. `tests/rls/test_rls_provisioning.py` asserts this against PostgreSQL's catalogues, not against a list in a migration, so a new tenant-scoped model without a policy fails a test. `practices` / `practice_memberships` being in that list is F-0009, and the user has said it must change.

- **A policy alone is not isolation.** PostgreSQL does not evaluate policies unless `relrowsecurity` is set on the table, so a table can have a perfect policy listed in `pg_policies` and be wide open. That bug shipped once and every other assertion still passed. Assert the `relforcerowsecurity` flag.

- **Build state is fresh this session** — the first non-stale run since the RLS closure. `pytest -q` from `modernized/gnucash-reimagined/`: **269 collected, 231 passed, 38 failed** on PostgreSQL 16.15. Per suite: accounting **56/56** (golden 40/40), business_documents **17/17**, reporting **18/18**, identity **52/65**, document_intelligence **7/32**, **rls 78/78**. The 38 failures were counted by directory, not assumed: **25 document_intelligence (B-0002) + 13 identity (T-0015)**, nothing else. `manage.py check` reports no issues; `makemigrations --check --dry-run` reports no changes. The upstream C/C++ tree was **not** built this session (T-0008).

- **The recurring defect pattern.** Phase E.1's "migrate models" step was recorded complete but was materially incomplete: services and support modules were dropped, and migrated code kept referring to things that never existed. Every unexplained failure so far has had that shape. When something is inexplicably red, suspect a reference to a legacy name before suspecting logic. The RLS session added three more of the same family — a middleware that had never run, a header trusted without a check, and policies created on tables where RLS was never enabled — all of which *looked* implemented. This session added a fourth: a provisioning statement that looked idempotent and was silently revoking a credential across the whole cluster.

- **Search tooling goes stale.** A "no callers found" result from a stale jcodemunch index is not evidence of absence. **Concretely: `common/rls/migrations/` is missing from the index entirely while the four files exist on disk** — a symbol or text search for anything in them returns nothing. Check `indexed_at` against the tree, and call `register_edit` with `reindex=true` after editing (LL-011).

- **Index state at close.** Code index refreshed and fully embedded (`embed_repo`: 32,972/32,972 symbols, voyage-code-2, 0 errors). Docs embedding coverage has been running low (~24%), so semantic/hybrid doc search ranks most of the corpus at zero — prefer `search_sections` (BM25) until a non-incremental `index_local` is run deliberately.

---

## Do NOT Do

- **Do not run more than three agents at once.** Standing user rule.
- **Do not run two Claude sessions against this working tree at once.** One has already discarded uncommitted work here (F-0008).
- **Do not drop `stash@{0}`.** It is the recovery backup for the RLS work.
- **Do not weaken, bypass, or add an escape hatch to any safeguard.** No `force=`, `_skip_validation`, `save_raw`, settings switch, session variable, bypass manager, or `BYPASSRLS` role. The accounting immutability guarantees and the tenant isolation boundary are the product's core value. If a test or fixture conflicts with a guard, fix the fixture.
- **Do not point `default` at the owning role, and do not add a privileged connection to the request path.** `deploy` exists for `migrate` and nothing else. The whole gain of the split is that the connection serving requests cannot see past a policy.
- **Do not grant `app_user` `SUPERUSER` or `BYPASSRLS`, and do not let it own a table.** Ownership is itself a bypass. `tests/rls/test_rls_provisioning.py` asserts all three.
- **Do not re-add `NOLOGIN` to the re-asserting `ALTER ROLE` in `common/rls/migrations/0001`.** Roles are cluster-scoped and that statement runs per database, so it revokes the runtime credential across the whole cluster every time a fresh database is migrated — which is every pytest run.
- **Do not make `rls.W001` iterate every alias.** `deploy` is expected to bypass; a per-alias check reports the correct configuration as a fault and would get switched off. It inspects the runtime alias only.
- **Do not run `manage.py migrate` without `--database=deploy`** in development or production. It cannot work, and the error is a permission failure rather than a helpful message.
- **Do not create a posted `JournalEntry` directly** (`is_posted=True` on create). Post through `PostingService` / `JournalEntry.post()`.
- **Do not call `document.mark_posted()` from outside `DocumentPostingService`.**
- **Do not re-add an unconditional `pytest.xfail(...)` inside a test body.** It silently disables every assertion below it.
- **Do not move the tenant authorization check out of `TenantContextMiddleware`, or gate it on `RLS_ENABLED`.** RLS confines a session to whatever tenant is in context; it cannot tell whether that tenant was the right one. `TenantContext` and `TenantContextManager` do no authorization of their own and must not be reached from request handling with a caller-supplied tenant.
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

> "/session-close, commit and push"

**Outcome:** committed in two checkpoints and pushed to `origin/modernization/reimagine-scaffold` (`0617189c20..4857c38858`). `9b0a6d6bcc` is the credential-split work — settings, the RLS check, the migration fix, four new tests, and the runbook in README, `compose.yml` and `docker/init-db.sql`. `4857c38858` carries the `.claude/` housekeeping that had been deliberately left uncommitted since the RLS session: the index-refresh step in `session-close` and the `jcodemunch`/`jdocmunch` rules. Session closed with `/session-close`.

Earlier in the session the user approved, via explicit choice, the three decisions the split turned on: the `deploy` alias reuses the existing privileged role rather than creating a new one; development takes the full split including `RLS_ENABLED = True`; and this machine's cluster could be changed to prove it end-to-end. All three are recorded in **Decisions passed** in `current-state.md`.

Standing constraints carried in **Do NOT Do** above.
