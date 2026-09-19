# Notes for Next Session

**Written:** 2026-09-19T14:11:07Z
**Status at Close:** IDLE. Branch `modernization/reimagine-scaffold`, work commit `2b638a4948`, pushed to `origin` with the Memory Bank commit directly on top. Working tree clean. Suite: **148 passed / 38 failed** of 186 on PostgreSQL 16.15.

---

## Priority Actions (do these first)

1. **T-0015 — Build the identity REST layer.** Thirteen tests, the entire remaining identity gap, and the next material win. Run first to confirm the baseline:
   ```bash
   cd modernized/gnucash-reimagined
   ~/.venvs/gnucash-reimagined/bin/python -m pytest tests/identity/integration/test_api.py -q
   ```
   The failing endpoints are `/api/v1/auth/me/`, login, register, tenant list/get/create, membership invite/list, and notification list/unread-count. The services underneath are implemented and green — this is serializers, viewsets and URL routes over working code, not new domain logic. `tests/identity/acceptance/test_authentication_rules.py::test_users_must_authenticate_before_accessing_tenant_resources` needs `/api/v1/auth/me/` too and is the 13th.

2. **B-0002 — Decide the document-intelligence test structure.** 25 of 32 tests subclass `unittest.TestCase` while their methods take pytest fixtures, which pytest cannot inject. Structural: no implementation work makes them pass. Choose between rewriting the classes as plain pytest classes or moving fixtures into `setUp()`. This is the other half of the remaining 38.

3. **B-0004 then B-0003 — provision RLS.** B-0004 first: `docker/init-db.sql` declares `get_current_user_id()` / `get_current_entity_id()` as `RETURNS integer` while every PK is a UUID, and `EXCEPTION WHEN OTHERS THEN RETURN NULL` swallows the failed cast, so policies would read NULL silently. Fix the return types, then write a `RunSQL` migration under `common/rls/` installing the functions and policies.

4. **Q-0004 — decide entity-scoped permission narrowing.** Blocks implementing `get_user_permissions` and collapsing the `has_permission` / `user_has_permission` duplication in `AuthorizationService`. `Membership.scoped_entity` (null = all entities) and `Role.tenant` (nullable) exist, but nothing defines how a role's permissions filter by entity, and the BR-AUTH-012 test marks itself a simplified stand-in. Guessing this bakes an unverified access-control semantic into the service layer.

5. **T-0014 — the unmanaged `ImmutablePostedJournal*` models break every ORM delete** of a journal entry or line: Django's deletion collector follows their relations and emits `DELETE FROM accounting_immutable_posted_journal_line`, which does not exist. Either give them real tables or take them out of the deletion path, then restore the ADR-010 ORM-delete test to assert the ADR-010 message specifically rather than bare `DatabaseError` (see LL-008).

6. **T-0016 — fix `Role.get_permissions()`.** `apps/identity/models/membership.py:113` reads `self.permissions`, which is not a field on `Role` — the link is the `RolePermission` through-model with `related_name='role_permissions'`. Every call raises `AttributeError`. `AuthorizationService.has_permission` deliberately routes around it with an explicit join; pick one path and make both use it.

7. **T-0008 — diagnose `test-qof` and `test-gnc-numeric`** in the *upstream* tree (unrelated to the reimagine work):
   ```bash
   cmake --build build && ctest --test-dir build -R "test-qof|test-gnc-numeric" --output-on-failure
   ```

**Waiting on the human (cannot be resolved by reading the tree):**

- **T-0007** — confirm the reimagine track is live and the same-stack uplift brief is dormant. Both claim approval on disk.
- **Q-0001** — confirm the off-limits trees (`borrowed/` + `contrib/` were proposed, never answered).
- **Q-0002** — sign off the five medium-confidence P0 rules before they harden into regression contracts.

Lower priority: **F-0001** (re-apply plugin-cache agent edits after a plugin update), **F-0002** (`FRONTEND_URL` and the `LLM_*` keys are undeclared settings read via `getattr` fallbacks), **F-0003** (project/cost-centre support belongs to a future Dimension model), **F-0004** (residual `TODO`/`NotImplementedError` markers by context — the identity ones now carry an explicit reason each, the rest do not), **F-0005** (MFA enrolment cannot persist its TOTP secret: the `User` model has no field for it, so `mfa_enabled` is an enrolment flag and not enforced MFA), **F-0006** (`ApiToken.revoke` still takes `revoked_by_user` while `AdvisorAccessGrant.revoke` now takes `revoked_by`).

---

## Context to Remember

- **Environment.** Tests run with `~/.venvs/gnucash-reimagined/bin/python -m pytest`, from `modernized/gnucash-reimagined/`. System `python3` has **no Django** — it will fail confusingly. There is deliberately **no venv inside the repo**: `.venv` is not gitignored. PostgreSQL 16.15 runs locally with `postgres`/`postgres`. **Docker is not installed**, so `compose.yml` is unusable and `docker/init-db.sql` never runs.

- **The test database.** `config/settings/test.py` points at `gnucash_test`, which pytest creates and drops itself. Do not create it by hand. If a run produces odd `relation "..." does not exist` errors that a re-run does not reproduce, suspect a leftover database from a previously-aborted run before suspecting the code — this happened once this session and vanished on the next clean run (LL-013).

- **Where the suite stands.** accounting **56/56** (golden **40/40**, ADR-010 **16/16**), reporting **18/18**, business_documents **15/15**, identity **52/65**, document_intelligence **7/32**. The 38 failures are exactly T-0015 (13) plus B-0002 (25) — nothing else.

- **Posting is now one atomic operation.** `DocumentPostingService.post_document()` locks the document with `select_for_update`, re-validates against the **locked** row rather than the caller's stale instance, posts through the accounting engine, calls `locked.mark_posted(user, journal_entry)`, writes a `DOCUMENT_POSTED` `AuditEvent`, and refreshes the caller's instance — all inside one `@transaction.atomic` block. The accounting engine's own `with transaction.atomic()` nests as a savepoint inside it. **Callers must not call `mark_posted()` themselves.** The rollback behaviour is by construction and has **not** been tested by fault injection; a test that forces a failure between posting and `mark_posted` would close that gap, and was offered to the user but not requested.

- **The identity services are class-level.** `AuthenticationService`, `AuthorizationService` and `TenantService` expose their contract methods as `@staticmethod`, because the tests call them on the class, not an instance. Access tokens are `django.core.signing` under the salt `identity.access_token` with a 12-hour max age; every validation failure mode returns `None` so a caller cannot distinguish forged from expired. `authenticate_user` hashes even on the no-such-user path to avoid a user-enumeration oracle. `can_access_tenant` requires direct membership **or** the full advisor chain (practice membership + active engagement + an active grant naming that user) — an engagement alone is not access.

- **The recurring defect pattern.** Phase E.1's "migrate models" step was recorded complete but was materially incomplete: **services and support modules were dropped** during consolidation, and migrated code kept referring to things that never existed. Every unexplained failure so far has had that shape. When something is inexplicably red, suspect a reference to a legacy name before suspecting logic. Concrete instances: a phantom `decimal-converter` PyPI dependency, a `Decimal` used in a def-time annotation with no import, 9 FKs pointing at `"auth.User"` with a swapped-out user model, `PostingService.create_reversal_entry` called on the wrong class, `DocumentPostingService` scaffolded against an imagined accounting API, and `ApiToken._generate_token()` emitting a token longer than its own column.

- **Two live tests can encode contradictory contracts.** `AdvisorAccessGrant.revoke` was called as `revoke(revoked_by=…)` by the acceptance test and `revoke(revoked_by_user=…)` by the unit test — in the same tree, a split inherited from the legacy tree, which is why the acceptance test could never have passed there either. Resolved toward the field name; the unit test's keyword was updated with its assertions untouched. See LL-012 before resolving the next such conflict.

- **Search tooling goes stale.** The jcodemunch index was built at 11:31 and was already wrong about files edited afterwards: `search_text` returned a method's *previous* docstring, and `get_file_outline` returned zero symbols for a file that plainly exists. A "no callers found" result from a stale index is not evidence of absence. Check `indexed_at` against the tree, and call `register_edit` with `reindex=true` after editing (LL-011).

- **A partial Memory Bank update happened mid-session.** `current-state.md` and this file both had their Branch/HEAD line corrected at ~13:42 (to `1f8972b30e`, pushed, clean) while every other section still described the previous session — and the scratchpad's `archive-resolved` ran at the same moment, archiving T-0009. Nothing in this session issued those writes. Read both files end to end at boot rather than trusting the header, and expect the "modified since read" guard to fire when rewriting them.

---

## Do NOT Do

- **Do not run more than three agents at once.** Standing user rule. (The rate-limit blocker that originally motivated it is closed, but the rule stands.)
- **Do not weaken, bypass, or add an escape hatch to any safeguard.** No `force=`, `_skip_validation`, `save_raw`, settings switch, session variable, or bypass manager. The accounting immutability guarantees are the product's core value. If a test or fixture conflicts with a guard, fix the fixture.
- **Do not create a posted `JournalEntry` directly** (`is_posted=True` on create). Post through `PostingService` / `JournalEntry.post()` so balance, fiscal-period and audit checks run.
- **Do not call `document.mark_posted()` from outside `DocumentPostingService`.** The service owns that transition now (see Decisions passed in `current-state.md`).
- **Do not re-add an unconditional `pytest.xfail(...)` inside a test body.** It silently disables every assertion below it. Two such calls were hiding a completely broken posting service.
- **Do not hand-edit `memory-bank/runtime/session-scratchpad.json`.** All mutations go through `.claude/scripts/session_scratchpad.py`.
- **Do not commit `memory-bank/runtime/`** — live per-session state, already gitignored.
- **Do not send anything from `analysis/` or `modernized/` upstream.** Fork branch only; upstream-bound work stays a minimal, reviewable diff against `main`.
- **Do not add or restore `accounting.Project`**, and do not re-add `DocumentLine.project`. Project/cost-centre support is future Dimension work.
- **Do not treat `mfa_enabled` as enforced MFA.** Nothing can verify a TOTP code, because no field holds the secret (F-0005).
- **Do not trust the artifact counts in `analysis/`** without re-deriving them from disk. They disagree with each other and with the transcripts.

---

## Human's Last Instruction

> `/session-close` — "and commit and push"

Before that, the two work directives that produced this session's results, in order:

1. *"Before [the identity-services task], make one small architectural correction to Business Documents."* — `DocumentPostingService.post_document()` should own the complete posting lifecycle, explicitly **not** preserving the legacy two-step caller contract, because it "creates a consistency window where a JournalEntry can be posted successfully while the AccountingDocument remains unposted." The required behaviour was enumerated as nine ordered steps inside a single transaction, with rollback of both the ledger posting and the document transition on any failure, and named assertions to replace the test's manual `mark_posted()` call. Stated as "an intentional improvement over the legacy behavior, not a compatibility regression." The gate for proceeding was accounting 56/56 and business_documents 15/15.
2. *"proceed directly to [the identity-services task] and implement the three missing Identity services against their contract tests."*

Bracketed substitutions above replace a scratchpad ID that has since been resolved, so the handoff checker does not read this section as a pending item. The wording is otherwise as spoken.

Standing constraints carried in **Do NOT Do** above.
