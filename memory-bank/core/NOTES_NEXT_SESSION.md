# Notes for Next Session

**Written:** 2026-09-19T18:36:27Z
**Status at Close:** IDLE. Branch `modernization/reimagine-scaffold` at `0617189c20`. **This session wrote no code** — it verified that the RLS closure was already committed at `290cc7e73e` and that nothing RLS-related was left uncommitted. The working tree's only changes are `.claude/` skill and rule files, deliberately not committed.

---

## Priority Actions (do these first)

1. **F-0007 — split the runtime and deploy database credentials. This is the user-directed next task, ahead of T-0015.** Today every environment connects as the `postgres` superuser, which bypasses RLS *even against a FORCEd table*. The 51 policed tables are correct and tested and currently subject to nothing at runtime. Deliverable: the web/Celery runtime connects as `app_user`; deployment and migrations connect as a deploy/owner role. `app_user` is **`NOLOGIN` today** — grant `LOGIN` and a password out of band before pointing anything at it. Watch for `DATABASES['default']` being a single alias shared by both paths; that is the structural reason this has not been done, and splitting it is the actual work. Acceptance: `manage.py check` stops emitting **`rls.W001`** with `RLS_ENABLED` on, and a runtime query with no tenant context returns zero rows instead of every tenant's rows. See `common/rls/checks.py` for the check and `config/settings/` for the connection definitions.

2. **T-0015 — build the identity REST layer.** 13 tests, the entire remaining identity gap. Run first to confirm the baseline:
   ```bash
   cd modernized/gnucash-reimagined
   ~/.venvs/gnucash-reimagined/bin/python -m pytest tests/identity/integration/test_api.py -q
   ```
   Failing endpoints: `/api/v1/auth/me/`, login, register, tenant list/get/create, membership invite/list, notification list/unread-count. The services underneath are implemented and green — this is serializers, viewsets and URL routes over working code.

   **The RLS closure added a constraint this endpoint work must satisfy.** A tenant-scoped request runs inside a transaction the middleware owns, with `app_user`'s policies applied:
   - `tenants` INSERT requires `get_current_user_id() IS NOT NULL AND created_by_id = get_current_user_id()`. The creating service must set `created_by`.
   - The follow-up `Membership` INSERT requires `app.current_tenant_id` to be set.
   - So **registration must `SET LOCAL` context to the tenant it just created, in the same transaction, using the id of the row it just inserted** — never a client-supplied id, or it becomes the arbitrary-tenant hole the middleware was rewritten to close.
   - Nothing enforces this in tests yet, because tests run as the `postgres` superuser and bypass RLS. **That is F-0007 again** — action 1 is what makes this constraint testable.

3. **F-0009 — scope Practice and PracticeMembership visibility.** User directive: they are global platform entities, but they **must not remain generally enumerable**. Minimum is a policy keyed to `user_id = get_current_user_id()`; if any callee needs a practice's full roster, introduce a practice-scoped GUC rather than widening the policy. Re-examine the advisor branch of `AuthorizationService.can_access_tenant()`, which joins through `practice_memberships`.

4. **B-0002 — Decide the document-intelligence test structure.** 25 of 32 tests subclass `unittest.TestCase` while their method signatures take pytest fixtures, which pytest cannot inject. Structural: no implementation work makes them pass. Choose between rewriting the classes as plain pytest classes or moving fixtures into `setUp()`. `tests/rls/` and `tests/business_documents/test_posting_atomicity.py` both use plain pytest functions with `pytestmark = pytest.mark.django_db(transaction=True)` — a working model.

5. **Q-0004 — decide entity-scoped permission narrowing.** Blocks implementing `get_user_permissions` and collapsing the `has_permission` / `user_has_permission` duplication in `AuthorizationService`. `Membership.scoped_entity` (null = all entities) and `Role.tenant` (nullable) exist, but nothing defines how a role's permissions filter by entity, and the BR-AUTH-012 test marks itself a simplified stand-in.

6. **T-0014 — the unmanaged `ImmutablePostedJournal*` models break every ORM delete** of a journal entry or line: Django's deletion collector follows their relations and emits `DELETE FROM accounting_immutable_posted_journal_line`, which does not exist. Either give them real tables or take them out of the deletion path, then restore the ADR-010 ORM-delete test to assert the ADR-010 message specifically rather than bare `DatabaseError` (LL-008).

7. **T-0008 — diagnose `test-qof` and `test-gnc-numeric`** in the *upstream* tree (unrelated to the reimagine work):
   ```bash
   cmake --build build && ctest --test-dir build -R "test-qof|test-gnc-numeric" --output-on-failure
   ```

**Waiting on the human (cannot be resolved by reading the tree):**

- **F-0008** — a second Claude session is active against this same working tree and has already discarded uncommitted work once. Confirm whether it has been stopped.
- **T-0007** — confirm the reimagine track is live and the same-stack uplift brief is dormant. Both claim approval on disk.
- **Q-0001** — confirm the off-limits trees (`borrowed/` + `contrib/` were proposed, never answered).
- **Q-0002** — sign off the five medium-confidence P0 rules before they harden into regression contracts.

Lower priority: **F-0001** (re-apply plugin-cache agent edits after a plugin update), **F-0002** (`FRONTEND_URL` and the `LLM_*` keys are undeclared settings read via `getattr` fallbacks), **F-0003** (project/cost-centre support belongs to a future Dimension model), **F-0004** (residual `TODO`/`NotImplementedError` markers by context), **F-0005** (MFA enrolment cannot persist its TOTP secret), **F-0006** (`ApiToken.revoke` still takes `revoked_by_user` while `AdvisorAccessGrant.revoke` takes `revoked_by`).

---

## Context to Remember

- **Nothing was committed this session, and nothing needed to be.** The RLS closure landed as `290cc7e73e` in the previous session. If you are asked to "commit the recovered RLS work", check `git log` before acting — the work is already in, and the only dirty paths are `.claude/` files.

- **The `.claude/` changes are uncommitted on purpose.** `M .claude/skills/session-close/SKILL.md` (+24/−2, adds a step 7 "Refresh the indexes") and `?? .claude/rules/` (`jcodemunch.md`, `jdocmunch.md`). They were excluded as unrelated to the RLS work. Re-check at the next close whether to keep, commit, or revert them.

- **`stash@{0}` (`wip-b0005-probe`) is retained as a recovery backup — do not drop it.** It holds 11 files, an older partial copy of the same RLS work, kept after a concurrent session's `git reset --hard` destroyed ~1600 uncommitted lines.

- **Two Claude sessions ran against this tree at once, and it cost real time.** One ran `git stash push -m wip-b0005-probe` + `git reset --hard HEAD`. The same two sessions shared the hard-coded `gnucash_test` database, which produced ~90 phantom failures that took a full bisect to attribute: `duplicate key ... auth_permission` after a truncated flush, `database "gnucash_test" does not exist` mid-run, and results that flipped between identical invocations. **Before bisecting a mystery failure, check whether another process owns the database.**

- **Environment.** Tests run with `~/.venvs/gnucash-reimagined/bin/python -m pytest`, from `modernized/gnucash-reimagined/`. System `python3` has **no Django**. PostgreSQL 16.15 runs locally with `postgres`/`postgres`, and **that role is a superuser, which bypasses RLS even against a FORCEd table** — the single most important fact for reading any RLS test, and the whole of F-0007. **Docker is not installed.**

- **The test database.** `config/settings/test.py` points at `gnucash_test`, created and dropped by pytest. Do not create it by hand. `app_user` is a **cluster-wide** role and survives test-database teardown.

- **How RLS is verified.** Every isolation assertion is made inside `tests/rls/conftest.py`'s `rls_session()` (drops to `app_user` with `SET LOCAL ROLE` and sets the GUCs via `set_config(..., true)`) or `app_role()`. Asserting through Django's own connection would pass no matter what the policies said.

- **Grep `APP_ROLE`, not `TO app_user`.** Policies are emitted as `TO {APP_ROLE}` from `APP_ROLE = "app_user"` in `common/rls/migrations/0004_tenant_isolation_closure.py`, so the literal string `TO app_user` appears nowhere in source. A grep for it returns zero and looks like a missing implementation.

- **Boundaries.** `common/rls` policies are named to `app_user`, `ENABLE` + `FORCE`, on 51 of 65 tables. The 14 unpoliced are global: 7 Django contrib, 2 auth M2M, `users`, `permissions`, `practices`, `practice_memberships`, `workflow_definitions`. `tests/rls/test_rls_provisioning.py` asserts this against PostgreSQL's catalogues, not against a list in a migration, so a new tenant-scoped model without a policy fails a test. `practices` / `practice_memberships` being in that list is F-0009, and the user has now said it must change.

- **A policy alone is not isolation.** PostgreSQL does not evaluate policies unless `relrowsecurity` is set on the table, so a table can have a perfect policy listed in `pg_policies` and be wide open. That bug shipped once and every other assertion still passed. Assert the `relforcerowsecurity` flag.

- **Build state is stale by one session.** No test suite ran this session. The last verified run is the previous session's, at `290cc7e73e`: **265 collected, 227 passed, 38 failed** on PostgreSQL 16.15. Per suite: accounting **56/56** (golden 40/40), business_documents **17/17**, reporting **18/18**, identity **52/65**, document_intelligence **7/32**, **rls 74/74**. The 38 failures are exactly T-0015 (13) plus B-0002 (25) — nothing else. The tree has not changed since except `memory-bank/` files, so this still describes the code, but **re-run before treating it as current**. The upstream C/C++ tree was last built 2026-09-18 (T-0008).

- **The recurring defect pattern.** Phase E.1's "migrate models" step was recorded complete but was materially incomplete: services and support modules were dropped, and migrated code kept referring to things that never existed. Every unexplained failure so far has had that shape. When something is inexplicably red, suspect a reference to a legacy name before suspecting logic. The RLS session added three more of the same family — a middleware that had never run, a header trusted without a check, and policies created on tables where RLS was never enabled — all of which *looked* implemented.

- **Search tooling goes stale.** A "no callers found" result from a stale jcodemunch index is not evidence of absence. Check `indexed_at` against the tree, and call `register_edit` with `reindex=true` after editing (LL-011).

- **Index state at close.** Refreshed at close of this session; see the closure record for the counts. Docs embedding coverage has been running low (~24%), so semantic/hybrid doc search ranks most of the corpus at zero — prefer `search_sections` (BM25) until a non-incremental `index_local` is run deliberately.

---

## Do NOT Do

- **Do not run more than three agents at once.** Standing user rule.
- **Do not run two Claude sessions against this working tree at once.** One has already discarded uncommitted work here (F-0008).
- **Do not drop `stash@{0}`.** It is the recovery backup for the RLS work.
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

> "Commit the recovered B-0005/RLS work now." — with five conditions: exclude the unrelated `.claude` skill/rule changes from the other session; do not drop `stash@{0}`; verify the working-tree diff contains all intended RLS/middleware/test changes; commit only the accounting/RLS changes as one checkpoint; then report remaining modified/untracked files. Followed by: "Then run /session-close." with explicit records to persist, and closing lines "Do not drop the recovery stash during session-close." and **"ignore the completed tasks above."**

**Outcome:** the commit step was already satisfied — the RLS work is `290cc7e73e`, committed in the previous session, and the working tree held no RLS changes to commit. Verification of that commit's contents is recorded in this session's `current-state.md` summary. Nothing was committed, and `stash@{0}` was left in place.

Standing constraints carried in **Do NOT Do** above.
